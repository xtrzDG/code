"""
A booking's side of its deposit: the status a held booking gets (PENDING
until the `booking_deposits` release gate opens, then PENDING_DEPOSIT),
which bookings may still take or keep a deposit, and the deposit summary
the booking carries for its list.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.deposits import BookingDeposit, DepositRequestDocument
from app.utilities.storage.release_gates import BOOKING_DEPOSITS_GATE, is_gate_open

# Statuses of a booking that still waits for its visit (and so may be held).
OPEN_BOOKING_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.PENDING_DEPOSIT, BookingStatus.CONFIRMED}
)
# Deposits that were paid and stay paid (counted as collected).
COLLECTED_DEPOSIT_STATUSES: frozenset[DepositStatus] = frozenset(
    {DepositStatus.PAID, DepositStatus.KEPT}
)
# Deposits a guest paid, whatever became of the money after.
PAID_DEPOSIT_STATUSES: frozenset[DepositStatus] = frozenset(
    {DepositStatus.PAID, DepositStatus.KEPT, DepositStatus.REFUND_DUE}
)


def held_status() -> BookingStatus:
    """The status of a booking whose place waits for its deposit."""

    if is_gate_open(BOOKING_DEPOSITS_GATE):
        return BookingStatus.PENDING_DEPOSIT

    return BookingStatus.PENDING


def is_held_for_deposit(booking: BookingDocument) -> bool:
    """The booking holds its place only until its deposit is paid."""

    return (
        booking.status in (BookingStatus.PENDING, BookingStatus.PENDING_DEPOSIT)
        and booking.deposit_status is DepositStatus.AWAITING
    )


def summarize(request: DepositRequestDocument) -> BookingDeposit:
    return BookingDeposit(
        request_id=request.id,
        status=request.status,
        amount_minor=request.amount_minor,
        currency_code=request.currency_code,
        hold_expires_at=(
            request.hold_expires_at
            if request.status is DepositStatus.AWAITING
            else None
        ),
    )


def show_deposit(
    booking: BookingDocument, request: DepositRequestDocument, now: Microseconds
) -> BookingDocument:
    """The booking with the request's summary (and its status at the top level)."""

    booking.deposit = summarize(request)
    booking.deposit_status = request.status
    booking.updated_at = now
    return booking
