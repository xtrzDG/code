from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.repositories import InvoiceRepoContract, SubscriptionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewSource,
    CancelSubscriptionCommand,
)
from app.use_cases.billing.billing_records import (
    list_open_invoices,
    list_subscription_invoices,
    require_current_subscription,
)


class CancelSubscriptionUseCase(
    UseCaseContract[CancelSubscriptionCommand, BillingOverview]
):
    """
    Owner cancels the subscription (the concept sells month to month).

    Automatic charges stop at the provider and unpaid invoices are voided.
    The assistant keeps full service until the end of the paid period (or
    the trial); then the grace job switches it to taking requests only.
    Cancelling twice changes nothing; a later checkout resumes the service.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
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
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ] = assemble_billing_overview
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CancelSubscriptionCommand) -> BillingOverview:
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
        if subscription.status is not SubscriptionStatus.CANCELLED:
            self._cancel(subscription)

        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=business,
                display_language=input_data.display_language,
            )
        )

    def _cancel(self, subscription: SubscriptionDocument) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        if subscription.provider_reference is not None:
            self._payment_gateway.stop_recurring(subscription.provider_reference)
            subscription.provider_reference = None

        for invoice in list_open_invoices(
            list_subscription_invoices(self._invoice_repo, subscription)
        ):
            invoice.status = InvoiceStatus.VOID
            invoice.updated_at = now
            self._invoice_repo.save(invoice)

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.grace_until = None
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
