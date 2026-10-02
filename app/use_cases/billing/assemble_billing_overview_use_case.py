from decimal import Decimal

from typed_time_provider import Microseconds, WallClock

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewSource,
    InvoiceView,
    PackageUsageView,
    SubscriptionView,
)
from app.schemas.dto.billing_ledger import PackageUsageTotals
from app.schemas.typings.billing.booleans import IsPriceEstimated
from app.schemas.typings.billing.constrained_integers import OverageVoiceMinutes
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.use_cases.billing.billing_records import (
    find_current_subscription,
    is_trial_available,
)
from app.use_cases.billing.package_usage import (
    compute_overage_minutes,
    compute_usage_percent,
    summarize_package_usage,
)
from app.use_cases.billing.subscription_pricing import (
    price_overage_per_minute,
    quote_money,
    select_subscription_currency,
)
from app.utilities.billing.billing_periods import find_usage_window
from app.utilities.localization.language_tags import require_babel_locale
from app.utilities.money.money_math import multiply_money

MAX_LISTED_INVOICES: int = 50


class AssembleBillingOverviewUseCase(
    UseCaseContract[BillingOverviewSource, BillingOverview]
):
    """
    Billing page of an already authorized business.

    Shows the current subscription (plan name in the reader's language,
    price, status, period, grace), package use in the billing window that
    contains now (voice minutes from VOICE_SECONDS events rounded up, dialogs
    from DIALOG events), minutes above the package with their price, and the
    newest invoices. The trial is offered until the business has started
    it or paid; a subscription still waiting for its first payment has no
    package yet.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        usage_event_repo: UsageEventRepoContract,
        plan_registry: PlanRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BillingOverviewSource) -> BillingOverview:
        business: BusinessDocument = input_data.business
        language: LanguageTag = input_data.display_language or business.owner_language
        require_babel_locale(language)
        subscriptions: list[SubscriptionDocument] = (
            self._subscription_repo.list_by_business(business.id)
        )
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo,
            business.id,
        )
        invoices: list[InvoiceDocument] = self._invoice_repo.list_by_business(
            business.id
        )[:MAX_LISTED_INVOICES]
        currency_code: CurrencyCode = (
            subscription.currency_code
            if subscription is not None
            else select_subscription_currency(
                self._plan_registry,
                business.plan_key,
                business.currency_code,
            )
        )
        return BillingOverview(
            business_id=business.id,
            display_language=language,
            currency_code=currency_code,
            service_mode=business.service_mode,
            is_trial_available=is_trial_available(subscriptions),
            subscription=(
                None
                if subscription is None
                else self._view_subscription(subscription, language)
            ),
            usage=(
                None
                if subscription is None
                or subscription.status is SubscriptionStatus.INCOMPLETE
                else self._view_usage(business, subscription, language)
            ),
            invoices=[self._view_invoice(invoice, language) for invoice in invoices],
        )

    def _view_subscription(
        self,
        subscription: SubscriptionDocument,
        language: LanguageTag,
    ) -> SubscriptionView:
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        return SubscriptionView(
            id=subscription.id,
            plan_key=subscription.plan_key,
            plan_name=self._localized_text_resolver.resolve(plan.names, language),
            billing_period=subscription.billing_period,
            status=subscription.status,
            price=quote_money(
                Money(
                    amount_minor=subscription.price_minor,
                    currency_code=subscription.currency_code,
                ),
                False,
                language,
            ),
            trial_ends_at=subscription.trial_ends_at,
            period_start=subscription.period_start,
            period_end=subscription.period_end,
            grace_until=subscription.grace_until,
            has_auto_debit=subscription.provider_reference is not None,
        )

    def _view_usage(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        language: LanguageTag,
    ) -> PackageUsageView:
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        window_start, window_end = find_usage_window(
            subscription,
            self._wall_clock.now_unix(),
            business.timezone,
        )
        totals: PackageUsageTotals = summarize_package_usage(
            self._usage_event_repo.list_by_business_between(
                business.id,
                window_start,
                window_end,
            ),
            window_start,
            window_end,
        )
        overage_minutes: OverageVoiceMinutes = compute_overage_minutes(
            totals.used_voice_minutes,
            int(plan.included_voice_minutes),
        )
        overage_price: Money
        is_estimated: IsPriceEstimated
        overage_price, is_estimated = price_overage_per_minute(
            plan,
            subscription.currency_code,
            self._exchange_rate_registry,
        )
        return PackageUsageView(
            period_start=window_start,
            period_end=window_end,
            used_voice_minutes=totals.used_voice_minutes,
            included_voice_minutes=plan.included_voice_minutes,
            voice_usage_percent=compute_usage_percent(
                int(totals.used_voice_minutes),
                int(plan.included_voice_minutes),
            ),
            used_dialogs=totals.used_dialogs,
            included_dialogs=plan.included_dialogs,
            dialog_usage_percent=compute_usage_percent(
                int(totals.used_dialogs),
                int(plan.included_dialogs),
            ),
            overage_voice_minutes=overage_minutes,
            overage_price_per_minute=quote_money(overage_price, is_estimated, language),
            overage_cost=quote_money(
                multiply_money(overage_price, Decimal(int(overage_minutes))),
                is_estimated,
                language,
            ),
        )

    def _view_invoice(
        self,
        invoice: InvoiceDocument,
        language: LanguageTag,
    ) -> InvoiceView:
        return InvoiceView(
            id=invoice.id,
            kind=invoice.kind,
            description=invoice.description,
            amount=quote_money(
                Money(
                    amount_minor=invoice.amount_minor,
                    currency_code=invoice.currency_code,
                ),
                False,
                language,
            ),
            status=invoice.status,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            issued_at=invoice.created_at,
        )
