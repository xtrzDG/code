from decimal import Decimal

from typed_time_provider import Microseconds, WallClock

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import (
    BusinessRepoContract,
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
    UserRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    BillingNoticeKind,
    InvoiceKind,
    InvoiceStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import (
    BillingNotice,
    InvoiceDescriptionInput,
    PackageUsageTotals,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.billing.constrained_integers import OverageVoiceMinutes
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.billing_records import (
    find_current_subscription,
    list_subscription_invoices,
    sum_invoice_amounts,
)
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.billing.package_usage import (
    compute_overage_minutes,
    summarize_package_usage,
)
from app.use_cases.billing.subscription_pricing import price_overage_per_minute
from app.utilities.billing.billing_periods import add_local_days, list_package_windows
from app.utilities.money.money_math import multiply_money

# Months older than this are not looked at again (usage of a closed month
# arrives within minutes; the bound keeps every run cheap).
OVERAGE_LOOKBACK_MICROSECONDS: int = 62 * 24 * 60 * 60 * 1_000_000


class InvoiceUsageOverageUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Background job: bill call minutes above the package (concept: 0.15 EUR
    a minute above the package, "безлимита нет").

    Packages are monthly whatever the billing interval, so every month of a
    paid service period that has ended is checked once: the voice minutes
    above the plan's package are invoiced (USAGE_OVERAGE) in the
    subscription currency at the plan's overage price. A month is billed
    at most once; the trial is never billed. Owners are told the amount
    and the deadline; the bill is paid at the next checkout, and while it
    stays unpaid the grace job makes the subscription past due, so after
    the plan's grace days the assistant only takes requests. Without an
    overage price in the subscription currency nothing is invented and
    nothing is billed.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        usage_event_repo: UsageEventRepoContract,
        user_repo: UserRepoContract,
        plan_registry: PlanRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        invoice_description_transformer: TransformerContract[
            InvoiceDescriptionInput,
            InvoiceDescription,
        ],
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._user_repo: UserRepoContract = user_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._invoice_description_transformer: TransformerContract[
            InvoiceDescriptionInput,
            InvoiceDescription,
        ] = invoice_description_transformer
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._billing_notice_transformer: TransformerContract[
            BillingNotice,
            MessageText,
        ] = billing_notice_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        issued_count: int = 0
        for business in self._business_repo.list_all():
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo,
                business.id,
            )
            if subscription is None:
                continue

            issued: list[InvoiceDocument] = self._invoice_business(
                business,
                subscription,
            )
            if issued != []:
                self._notify(business, subscription, issued)
                issued_count += len(issued)

        return JobReport(processed_count=ProcessedItemCount(issued_count))

    def _invoice_business(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
    ) -> list[InvoiceDocument]:
        now: Microseconds = self._wall_clock.now_unix()
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        price_per_minute: Money
        price_per_minute, _ = price_overage_per_minute(
            plan,
            subscription.currency_code,
            self._exchange_rate_registry,
        )
        if price_per_minute.currency_code != subscription.currency_code:
            return []

        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo,
            subscription,
        )
        billed_starts: set[Microseconds] = {
            invoice.period_start
            for invoice in invoices
            if invoice.kind is InvoiceKind.USAGE_OVERAGE
            and invoice.status is not InvoiceStatus.VOID
        }
        issued: list[InvoiceDocument] = []
        for paid_period in invoices:
            if (
                paid_period.kind is not InvoiceKind.SERVICE_PERIOD
                or paid_period.status is not InvoiceStatus.PAID
            ):
                continue

            for window_start, window_end in list_package_windows(
                paid_period.period_start,
                paid_period.period_end,
                business.timezone,
            ):
                if (
                    window_end > now
                    or int(window_end) <= int(now) - OVERAGE_LOOKBACK_MICROSECONDS
                    or window_start in billed_starts
                ):
                    continue

                invoice: InvoiceDocument | None = self._invoice_window(
                    business,
                    subscription,
                    plan,
                    price_per_minute,
                    window_start,
                    window_end,
                )
                billed_starts.add(window_start)
                if invoice is not None:
                    issued.append(invoice)

        return issued

    def _invoice_window(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        plan: PlanDefinition,
        price_per_minute: Money,
        window_start: Microseconds,
        window_end: Microseconds,
    ) -> InvoiceDocument | None:
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
        if int(overage_minutes) == 0:
            return None

        amount: Money = multiply_money(price_per_minute, Decimal(int(overage_minutes)))
        now: Microseconds = self._wall_clock.now_unix()
        invoice = InvoiceDocument(
            business_id=business.id,
            subscription_id=subscription.id,
            kind=InvoiceKind.USAGE_OVERAGE,
            description=self._invoice_description_transformer.transform(
                InvoiceDescriptionInput(
                    kind=InvoiceKind.USAGE_OVERAGE,
                    language=business.owner_language,
                    timezone=business.timezone,
                    plan_names=plan.names,
                    billing_period=subscription.billing_period,
                    period_start=window_start,
                    period_end=window_end,
                    overage_voice_minutes=overage_minutes,
                )
            ),
            amount_minor=amount.amount_minor,
            currency_code=amount.currency_code,
            status=InvoiceStatus.ISSUED,
            period_start=window_start,
            period_end=window_end,
            created_at=now,
            updated_at=now,
        )
        self._invoice_repo.save(invoice)
        return invoice

    def _notify(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        issued: list[InvoiceDocument],
    ) -> None:
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(
                BillingNotice(
                    kind=BillingNoticeKind.OVERAGE_INVOICED,
                    language=business.owner_language,
                    timezone=business.timezone,
                    business_name=business.name,
                    amount=sum_invoice_amounts(issued),
                    deadline=add_local_days(
                        self._wall_clock.now_unix(),
                        int(plan.grace_period_days),
                        business.timezone,
                    ),
                )
            ),
        )
