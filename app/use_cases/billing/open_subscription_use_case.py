from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import (
    BusinessRepoContract,
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_cabinet import (
    SubscribeCommand,
    SubscribeRequest,
    SubscriptionOpening,
)
from app.schemas.typings.billing.booleans import IsSubscriptionCreated
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.billing.billing_records import (
    find_current_subscription,
    list_open_invoices,
    list_subscription_invoices,
)
from app.use_cases.billing.subscription_pricing import (
    price_subscription,
    select_subscription_currency,
)
from app.utilities.billing.return_urls import require_allowed_return_url


class OpenSubscriptionUseCase(UseCaseContract[SubscribeCommand, SubscriptionOpening]):
    """
    First step of subscribing with payment now (after the trial, or
    without one): make sure the business has a subscription to pay for.

    The return page is checked before anything changes. A business without
    any subscription gets one for the chosen plan and period, priced like
    the trial would be (business currency when the price book has it,
    otherwise EUR) and INCOMPLETE until its first payment: no service, no
    trial used, and the chosen plan becomes the business plan. An existing
    subscription is left as it is (the plan change is a separate step); one
    still INCOMPLETE is re-dated to now and its unpaid service periods are
    voided, so the owner never pays for days before the payment.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        plan_registry: PlanRegistryContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SubscribeCommand) -> SubscriptionOpening:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        require_allowed_return_url(input_data.request.return_url, self._app_settings)
        now: Microseconds = self._wall_clock.now_unix()
        current: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo,
            business.id,
        )
        if current is None:
            return SubscriptionOpening(
                subscription_id=self._open(business, input_data.request, now).id,
                is_created=IsSubscriptionCreated(True),
            )

        if current.status is SubscriptionStatus.INCOMPLETE:
            self._redate_unpaid(current, now)

        return SubscriptionOpening(
            subscription_id=current.id,
            is_created=IsSubscriptionCreated(False),
        )

    def _open(
        self,
        business: BusinessDocument,
        request: SubscribeRequest,
        now: Microseconds,
    ) -> SubscriptionDocument:
        currency_code: CurrencyCode = select_subscription_currency(
            self._plan_registry,
            request.plan_key,
            business.currency_code,
        )
        price: Money = price_subscription(
            self._plan_registry,
            request.plan_key,
            request.billing_period,
            currency_code,
        )
        subscription = SubscriptionDocument(
            business_id=business.id,
            plan_key=request.plan_key,
            billing_period=request.billing_period,
            price_minor=price.amount_minor,
            currency_code=price.currency_code,
            status=SubscriptionStatus.INCOMPLETE,
            period_start=now,
            period_end=now,
            created_at=now,
            updated_at=now,
        )
        self._subscription_repo.save(subscription)

        def choose_plan(current: BusinessDocument) -> None:
            # Changed on the business as stored now, so an edit saved
            # meanwhile is kept.
            current.plan_key = request.plan_key
            current.updated_at = now

        self._business_repo.update(business.id, choose_plan)
        return subscription

    def _redate_unpaid(
        self,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> None:
        stale_periods: list[InvoiceDocument] = [
            invoice
            for invoice in list_open_invoices(
                list_subscription_invoices(self._invoice_repo, subscription)
            )
            if invoice.kind is InvoiceKind.SERVICE_PERIOD and invoice.period_start < now
        ]
        for invoice in stale_periods:
            invoice.status = InvoiceStatus.VOID
            invoice.updated_at = now
            self._invoice_repo.save(invoice)

        subscription.period_start = now
        subscription.period_end = now
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
