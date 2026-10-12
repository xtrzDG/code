"""
Letting a lapsed hold go: under the business's booking lock, a deposit
still AWAITING whose hold ran out becomes EXPIRED, and the booking held
for it is cancelled (its place goes back, to the waitlist first). A
payment marked a moment earlier wins: the deposit is then PAID and
nothing is released.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.operations import BusinessLockRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.utilities.deposits.booking_deposit_state import (
    is_held_for_deposit,
    show_deposit,
)


@dataclass(frozen=True)
class ReleasedHold:
    """A deposit that lapsed, and the booking it released (if one was held)."""

    request: DepositRequestDocument
    booking: BookingDocument | None
    was_booking_held: bool


@dataclass(frozen=True)
class DepositHoldRelease:
    request_repo: DepositRequestRepoContract
    booking_repo: BookingRepoContract
    lock_registry: BusinessLockRegistryContract

    def release(
        self, request: DepositRequestDocument, now: Microseconds
    ) -> ReleasedHold | None:
        """None when the deposit moved on meanwhile (paid, cancelled)."""

        with self.lock_registry.lock_for(request.business_id):
            lapsed = self.request_repo.update(
                request.business_id, request.id, lambda stored: lapse(stored, now)
            )
            if lapsed is None:
                return None

            if lapsed.booking_id is None:
                return ReleasedHold(lapsed, None, False)

            before: BookingDocument | None = self.booking_repo.get(
                request.business_id, lapsed.booking_id
            )
            was_held: bool = before is not None and is_held_for_deposit(before)
            booking = self.booking_repo.update(
                request.business_id,
                lapsed.booking_id,
                lambda held: release_booking(held, lapsed, now),
            )
        return ReleasedHold(lapsed, booking, was_held)


def lapse(
    request: DepositRequestDocument, now: Microseconds
) -> DepositRequestDocument | None:
    if request.status is not DepositStatus.AWAITING or int(
        request.hold_expires_at
    ) > int(now):
        return None

    request.status = DepositStatus.EXPIRED
    request.reminder_due_at = None
    request.updated_at = now
    return request


def release_booking(
    booking: BookingDocument, request: DepositRequestDocument, now: Microseconds
) -> BookingDocument | None:
    """
    The booking held for this deposit is cancelled; one the customer or
    staff moved on already (cancelled, confirmed by hand) only shows the
    deposit's end.
    """

    if booking.deposit is None or booking.deposit.request_id != request.id:
        return None

    if is_held_for_deposit(booking):
        booking.status = BookingStatus.CANCELLED
        booking.last_status_change = None

    return show_deposit(booking, request, now)
