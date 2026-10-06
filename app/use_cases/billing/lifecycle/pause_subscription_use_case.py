from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.subscription_lifecycle import (
    SubscriptionLifecyclePolicyRegistryContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_cabinet import BillingOverview, BillingOverviewSource
from app.schemas.dto.subscription_lifecycle import (
    PauseAvailability,
    PauseSubscriptionCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.billing.lifecycle.lifecycle_events import lifecycle_event
from app.use_cases.billing.lifecycle.pause_availability import (
    read_pause_availability,
)
from app.use_cases.shared.billing_records import (
    list_open_invoices,
    list_subscription_invoices,
    require_current_subscription,
)
from app.utilities.billing.billing_periods import add_calendar_months


class PauseSubscriptionUseCase(
    UseCaseContract[PauseSubscriptionCommand, BillingOverview]
):
    """
    POST /v1/businesses/{business_id}/billing/pause: an owner pauses a paid
    monthly subscription for the season, for whole months from the end of
    what is paid, at most four months in any twelve.

    The paid period runs to its end at full service; then the pause job
    makes the subscription PAUSED: the assistant takes requests only, the
    channels stay connected, and each paused month is billed at its share
    of the price. Automatic charges at the full price stop now (a checkout
    of the pause fee starts them again from the pause's end). Refused
    (409) while pausing is off, the subscription is not active and monthly,
    a pause is already set, or the months do not fit the cap.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        subscription_event_repo: SubscriptionEventRepoContract,
        payment_gateway: PaymentGatewayAdapterContract,
        lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract,
        app_settings: AppSettings,
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
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract = (
            lifecycle_policy_registry
        )
        self._app_settings: AppSettings = app_settings
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource, BillingOverview
        ] = assemble_billing_overview
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PauseSubscriptionCommand) -> BillingOverview:
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
        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo, subscription
        )
        availability: PauseAvailability = read_pause_availability(
            business,
            subscription,
            invoices,
            self._subscription_event_repo.list_by_business(business.id),
            self._lifecycle_policy_registry.policy(),
            self._app_settings.growth.is_subscription_pause_enabled,
        )
        if availability.unavailable_reason is not None:
            raise ConflictError(
                "The subscription cannot be paused now "
                f"({availability.unavailable_reason.value})."
            )

        months: int = int(input_data.request.months)
        if availability.starts_at is None or months > int(availability.max_months):
            raise ConflictError(
                f"At most {int(availability.max_months)} months can be paused now."
            )

        self._schedule(
            business, subscription, invoices, availability.starts_at, input_data
        )
        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=business, display_language=input_data.display_language
            )
        )

    def _schedule(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        invoices: list[InvoiceDocument],
        starts_at: Microseconds,
        input_data: PauseSubscriptionCommand,
    ) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        if subscription.provider_reference is not None:
            self._payment_gateway.stop_recurring(subscription.provider_reference)
            subscription.provider_reference = None

        for invoice in list_open_invoices(invoices):
            # A renewal billed ahead for a period the pause now covers.
            if invoice.kind is InvoiceKind.SERVICE_PERIOD and int(
                invoice.period_start
            ) >= int(starts_at):
                invoice.status = InvoiceStatus.VOID
                invoice.updated_at = now
                self._invoice_repo.save(invoice)

        subscription.pause_starts_at = starts_at
        subscription.pause_until = add_calendar_months(
            starts_at, int(input_data.request.months), business.timezone
        )
        subscription.updated_at = now
        self._subscription_repo.save(subscription)
        scheduled: SubscriptionEventDocument = lifecycle_event(
            subscription,
            SubscriptionEventKind.PAUSE_SCHEDULED,
            now,
            input_data.user_id,
        )
        self._subscription_event_repo.record(
            scheduled.model_copy(update={"pause_months": input_data.request.months})
        )
