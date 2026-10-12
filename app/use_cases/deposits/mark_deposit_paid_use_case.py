from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.operations import BusinessLockRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.deposits import DepositRefusalCode, DepositStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deposits.deposit_views import (
    DepositRequestView,
    MarkDepositPaidCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.deposits.deposit_request_views import build_request_view
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.deposits.booking_deposit_state import show_deposit
from app.utilities.deposits.deposit_refusals import deposit_conflict

DEPOSIT_REQUEST_ENTITY: AuditEntityName = AuditEntityName("deposit_request")
HELD_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.PENDING_DEPOSIT}
)


class MarkDepositPaidUseCase(
    UseCaseContract[MarkDepositPaidCommand, DepositRequestView]
):
    """
    Staff saw the deposit in their own merchant account ("Paid" in the
    cabinet): the deposit becomes PAID with who marked it and when, no
    reminder goes, and a booking held for it is confirmed. Under the
    business's booking lock, so it never crosses the release of the hold:
    whichever comes first wins, and a deposit whose hold ran out (the place
    went back) is refused with STATUS_CHANGED. Marking a paid deposit again
    changes nothing. Owners and staff; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        deposit_request_repo: DepositRequestRepoContract,
        deposit_settings_repo: DepositSettingsRepoContract,
        booking_repo: BookingRepoContract,
        lock_registry: BusinessLockRegistryContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._request_repo: DepositRequestRepoContract = deposit_request_repo
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MarkDepositPaidCommand) -> DepositRequestView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        with self._lock_registry.lock_for(business.id):
            stored = self._request_repo.get(business.id, input_data.request_id)
            if stored is None:
                raise NotFoundError(f"Deposit {input_data.request_id} was not found.")

            if stored.status is DepositStatus.PAID:
                return build_request_view(
                    stored, self._settings_repo.get_by_business(business.id)
                )

            paid = self._request_repo.update(
                business.id,
                stored.id,
                lambda request: mark_paid(request, input_data.user_id, now),
            )
            if paid is None:
                raise deposit_conflict(
                    DepositRefusalCode.STATUS_CHANGED,
                    f"The deposit is {stored.status} and can no longer be marked "
                    "paid: its hold ran out or the booking ended.",
                )

            booking: BookingDocument | None = None
            if paid.booking_id is not None:
                booking = self._booking_repo.update(
                    business.id,
                    paid.booking_id,
                    lambda held: confirm_booking(held, paid, now),
                )

        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.UPDATE,
                DEPOSIT_REQUEST_ENTITY,
                str(paid.id),
                now,
            )
        )
        if booking is not None:
            self._live_events.publish(
                business.id,
                LiveEventKind.BOOKING_CHANGED,
                (booking.id,),
                is_sandbox=booking.is_sandbox,
            )
        return build_request_view(
            paid, self._settings_repo.get_by_business(business.id)
        )


def mark_paid(
    request: DepositRequestDocument, user_id: UserId, now: Microseconds
) -> DepositRequestDocument | None:
    if request.status is not DepositStatus.AWAITING:
        return None

    request.status = DepositStatus.PAID
    request.paid_at = now
    request.marked_paid_by = user_id
    request.reminder_due_at = None
    request.updated_at = now
    return request


def confirm_booking(
    booking: BookingDocument, request: DepositRequestDocument, now: Microseconds
) -> BookingDocument | None:
    """A booking held for this deposit is confirmed; any other keeps its status."""

    if booking.deposit is None or booking.deposit.request_id != request.id:
        return None

    if booking.status in HELD_STATUSES:
        booking.status = BookingStatus.CONFIRMED
        booking.last_status_change = None

    return show_deposit(booking, request, now)
