from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.operations import BusinessLockRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import (
    DepositExemption,
    DepositStatus,
    PaymentLinkOutcome,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositRequestDocument, DepositSettingsDocument
from app.schemas.dto.deposits.payment_link_requests import (
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
)
from app.use_cases.deposits.deposit_issuing import DepositIssuing, subject_of
from app.use_cases.deposits.deposit_quotes import (
    QuotedDeposit,
    quote_banquet,
    quote_booking,
)
from app.use_cases.deposits.deposit_subjects import DepositSubjects
from app.use_cases.shared.business_access import require_business
from app.utilities.deposits.booking_deposit_state import (
    OPEN_BOOKING_STATUSES,
    PAID_DEPOSIT_STATUSES,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


class SendPaymentLinkUseCase(
    UseCaseContract[SendPaymentLinkCommand, PaymentLinkReceipt]
):
    """
    The model tool send_payment_link: the deposit of the customer's own
    booking or banquet request (the one named, else the latest of this
    conversation). The amount comes from the business's policy and the link
    from the owner's own payment page, never from the model. A new deposit
    is stored AWAITING with its reference, the booking keeps its place
    until the hold ends (PENDING until the release gate opens, then
    PENDING_DEPOSIT), and the payment line in the customer's language goes
    under the reply; a deposit already waiting is sent again unchanged. A
    paid one is not asked again, nor one no policy covers (NOT_REQUIRED
    with the reason). Under the business's booking lock, so a hold, a
    payment marked and a release never cross.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        deposit_settings_repo: DepositSettingsRepoContract,
        deposit_request_repo: DepositRequestRepoContract,
        subjects: DepositSubjects,
        issuing: DepositIssuing,
        lock_registry: BusinessLockRegistryContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._request_repo: DepositRequestRepoContract = deposit_request_repo
        self._subjects: DepositSubjects = subjects
        self._issuing: DepositIssuing = issuing
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SendPaymentLinkCommand) -> PaymentLinkReceipt:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        settings: DepositSettingsDocument | None = self._settings_repo.get_by_business(
            business.id
        )
        if settings is None or not settings.is_enabled:
            return not_required(DepositExemption.DEPOSITS_OFF)

        now: Microseconds = self._wall_clock.now_unix()
        with self._lock_registry.lock_for(business.id):
            subject = self._subjects.find(input_data)
            if subject is None or not is_still_open(subject, now):
                return not_required(DepositExemption.NOTHING_OPEN)

            earlier: list[DepositRequestDocument] = self._earlier_requests(subject)
            waiting = next(
                (r for r in earlier if r.status is DepositStatus.AWAITING), None
            )
            if waiting is not None:
                return self._issuing.receipt(business, settings, waiting, now)

            if any(request.status in PAID_DEPOSIT_STATUSES for request in earlier):
                return PaymentLinkReceipt(
                    outcome=PaymentLinkOutcome.ALREADY_PAID,
                    subject=subject_of(subject),
                    booking_id=subject.id
                    if isinstance(subject, BookingDocument)
                    else None,
                    lead_id=subject.id if isinstance(subject, LeadDocument) else None,
                )

            quoted: QuotedDeposit = (
                quote_booking(settings, subject, business.currency_code)
                if isinstance(subject, BookingDocument)
                else quote_banquet(settings, subject, business.currency_code)
            )
            if quoted.amount is None:
                return not_required(quoted.exemption or DepositExemption.NO_POLICY)

            request = self._issuing.issue(settings, subject, quoted, input_data, now)

        if isinstance(subject, BookingDocument):
            self._live_events.publish(
                business.id,
                LiveEventKind.BOOKING_CHANGED,
                (subject.id,),
                is_sandbox=subject.is_sandbox,
            )
        return self._issuing.receipt(business, settings, request, now)

    def _earlier_requests(
        self, subject: BookingDocument | LeadDocument
    ) -> list[DepositRequestDocument]:
        if isinstance(subject, BookingDocument):
            return self._request_repo.list_of_booking(subject.business_id, subject.id)

        return self._request_repo.list_of_lead(subject.business_id, subject.id)


def is_still_open(subject: BookingDocument | LeadDocument, now: Microseconds) -> bool:
    """A booking not started yet that still waits for its visit; any open request."""

    if isinstance(subject, LeadDocument):
        return True

    starts_at: int = int(subject.starts_at) * MICROSECONDS_PER_SECOND
    return subject.status in OPEN_BOOKING_STATUSES and starts_at > int(now)


def not_required(exemption: DepositExemption) -> PaymentLinkReceipt:
    return PaymentLinkReceipt(
        outcome=PaymentLinkOutcome.NOT_REQUIRED, exemption=exemption
    )
