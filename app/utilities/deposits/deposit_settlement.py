"""
What becomes of a paid deposit when its booking ends: cancelled at least
the refund cutoff before the start, it goes back (REFUND_DUE, refunded by
staff in their merchant account); cancelled later or not come, it is kept
(KEPT); a booking that went on after all (an undone cancellation) keeps
it PAID.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.deposits.constrained_integers import DepositRefundCutoffHours

MICROSECONDS_PER_HOUR: int = 3600 * 1_000_000
MICROSECONDS_PER_SECOND: int = 1_000_000
# The cabinet lets staff undo a status change for ten minutes
# (bookings' UNDO_WINDOW_SECONDS); a staff cancellation is settled a minute
# after it, so an undone cancellation never refunds anything.
STAFF_SETTLE_DELAY_SECONDS: int = 11 * 60


def settled_status(
    booking_status: BookingStatus | None,
    starts_at: BookingStartsAtUnixSeconds | None,
    cancelled_at: Microseconds | None,
    refund_cutoff: DepositRefundCutoffHours,
) -> DepositStatus:
    """The paid deposit's state for its booking's end (a missing booking: kept)."""

    if booking_status is BookingStatus.NO_SHOW or booking_status is None:
        return DepositStatus.KEPT

    if booking_status is not BookingStatus.CANCELLED:
        return DepositStatus.PAID

    if starts_at is None or cancelled_at is None:
        return DepositStatus.KEPT

    last_free_moment: int = (
        int(starts_at) * MICROSECONDS_PER_SECOND
        - int(refund_cutoff) * MICROSECONDS_PER_HOUR
    )
    if int(cancelled_at) <= last_free_moment:
        return DepositStatus.REFUND_DUE

    return DepositStatus.KEPT


def settle_after(now: Microseconds, is_staff_change: bool) -> Microseconds:
    """When to decide: at once for a customer, after the undo window for staff."""

    delay: int = STAFF_SETTLE_DELAY_SECONDS if is_staff_change else 0
    return Microseconds(int(now) + delay * MICROSECONDS_PER_SECOND)
