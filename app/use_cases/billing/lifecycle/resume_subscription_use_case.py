from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_cabinet import BillingOverview, BillingOverviewSource
from app.schemas.dto.subscription_lifecycle import ResumeSubscriptionCommand
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.billing.lifecycle.lifecycle_events import (
    clear_pause,
    pause_ended_event,
)
from app.use_cases.billing.service_mode_switch import switch_service_mode
from app.use_cases.shared.billing_records import (
    OPEN_INVOICE_STATUSES,
    list_subscription_invoices,
    require_current_subscription,
)


class ResumeSubscriptionUseCase(
    UseCaseContract[ResumeSubscriptionCommand, BillingOverview]
):
    """
    POST /v1/businesses/{business_id}/billing/resume: the owner calls off a
    scheduled pause, or ends a running one.

    - Scheduled, not started: the pause is called off and counts no month;
      automatic charges stay off until the next payment turns them on.
    - Running, its current month unpaid: that month's bill is voided and
      full service is back now; the next period is due at once (the
      renewal flow bills it, with the plan's grace to pay).
    - Running, its current month paid: the pause ends when that month does
      (the pause job resumes it then); a paid month is never charged twice.

    Refused (409) without a pause.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        subscription_event_repo: SubscriptionEventRepoContract,
        payment_gateway: PaymentGatewayAdapterContract,
        assemble_billing_overview: UseCaseContract[
            BillingOverviewSource, BillingOverview
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource, BillingOverview
        ] = assemble_billing_overview
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ResumeSubscriptionCommand) -> BillingOverview:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo, business.id
        )
        if subscription.pause_starts_at is None or subscription.pause_until is None:
            raise ConflictError("The subscription has no pause to end.")

        now: Microseconds = self._wall_clock.now_unix()
        if subscription.status is SubscriptionStatus.PAUSED:
            self._end_running(business, subscription, input_data, now)
        else:
            self._record(pause_ended_event(subscription, now, input_data.user_id))
            clear_pause(subscription)
            subscription.updated_at = now
            self._subscription_repo.save(subscription)

        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=self._business_repo.get(business.id) or business,
                display_language=input_data.display_language,
            )
        )

    def _end_running(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        input_data: ResumeSubscriptionCommand,
        now: Microseconds,
    ) -> None:
        month: InvoiceDocument | None = self._current_month(subscription)
        if (
            month is not None
            and month.status is InvoiceStatus.PAID
            and now < month.period_end
        ):
            # The paid month runs out; the pause job resumes then.
            subscription.pause_until = min(
                month.period_end, subscription.pause_until or month.period_end, key=int
            )
            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            return

        if month is not None and month.status in OPEN_INVOICE_STATUSES:
            month.status = InvoiceStatus.VOID
            month.updated_at = now
            self._invoice_repo.save(month)

        ended: SubscriptionEventDocument | None = pause_ended_event(
            subscription, now, input_data.user_id
        )
        if subscription.provider_reference is not None:
            # A schedule a pause checkout started from the pause's end.
            self._payment_gateway.stop_recurring(subscription.provider_reference)
            subscription.provider_reference = None

        subscription.status = SubscriptionStatus.ACTIVE
        subscription.period_end = now
        subscription.grace_until = None
        clear_pause(subscription)
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        switch_service_mode(self._business_repo, business, ServiceMode.FULL, now)
        self._record(ended)

    def _current_month(
        self, subscription: SubscriptionDocument
    ) -> InvoiceDocument | None:
        for invoice in list_subscription_invoices(self._invoice_repo, subscription):
            if (
                invoice.kind is InvoiceKind.SERVICE_PERIOD
                and invoice.status is not InvoiceStatus.VOID
                and invoice.period_start == subscription.period_start
            ):
                return invoice

        return None

    def _record(self, event: SubscriptionEventDocument | None) -> None:
        if event is not None:
            self._subscription_event_repo.record(event)
