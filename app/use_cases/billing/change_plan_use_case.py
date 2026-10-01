from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import (
    BusinessRepoContract,
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import BillingPeriod, InvoiceKind, InvoiceStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewSource,
    ChangePlanCommand,
)
from app.use_cases.billing.billing_records import (
    list_open_invoices,
    list_subscription_invoices,
    require_current_subscription,
)
from app.use_cases.billing.subscription_pricing import price_subscription


class ChangePlanUseCase(UseCaseContract[ChangePlanCommand, BillingOverview]):
    """
    Owner switches plan or billing period (monthly or annual).

    The price stays in the subscription currency; annual is twelve months
    minus the annual discount, rounded in minor units. The package changes
    at once; the new price applies from the next invoice. When the price or
    the charge interval changes, automatic charges at the old price are
    stopped at the provider and unpaid invoices at the old price are voided,
    so the owner pays the new price at the next checkout. Moving to annual
    voids an unpaid setup fee: an annual payment includes it.
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
        payment_gateway: PaymentGatewayAdapterContract,
        assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ],
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
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ] = assemble_billing_overview
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ChangePlanCommand) -> BillingOverview:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo,
            business.id,
        )
        new_price: Money = price_subscription(
            self._plan_registry,
            input_data.request.plan_key,
            input_data.request.billing_period,
            subscription.currency_code,
        )
        is_charge_changed: bool = (
            new_price.amount_minor != subscription.price_minor
            or input_data.request.billing_period is not subscription.billing_period
        )
        if (
            not is_charge_changed
            and input_data.request.plan_key is subscription.plan_key
        ):
            return self._overview(business, input_data)

        now: Microseconds = self._wall_clock.now_unix()
        if is_charge_changed and subscription.provider_reference is not None:
            self._payment_gateway.stop_recurring(subscription.provider_reference)
            subscription.provider_reference = None

        self._void_outdated_invoices(
            subscription,
            input_data.request.billing_period,
            is_charge_changed,
            now,
        )
        subscription.plan_key = input_data.request.plan_key
        subscription.billing_period = input_data.request.billing_period
        subscription.price_minor = new_price.amount_minor
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        business.plan_key = input_data.request.plan_key
        business.updated_at = now
        self._business_repo.save(business)
        return self._overview(business, input_data)

    def _void_outdated_invoices(
        self,
        subscription: SubscriptionDocument,
        billing_period: BillingPeriod,
        is_charge_changed: bool,
        now: Microseconds,
    ) -> None:
        open_invoices: list[InvoiceDocument] = list_open_invoices(
            list_subscription_invoices(self._invoice_repo, subscription)
        )
        for invoice in open_invoices:
            is_outdated_period: bool = (
                invoice.kind is InvoiceKind.SERVICE_PERIOD and is_charge_changed
            )
            is_included_setup_fee: bool = (
                invoice.kind is InvoiceKind.SETUP_FEE
                and billing_period is BillingPeriod.ANNUAL
            )
            if is_outdated_period or is_included_setup_fee:
                invoice.status = InvoiceStatus.VOID
                invoice.updated_at = now
                self._invoice_repo.save(invoice)

    def _overview(
        self,
        business: BusinessDocument,
        input_data: ChangePlanCommand,
    ) -> BillingOverview:
        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=business,
                display_language=input_data.display_language,
            )
        )
