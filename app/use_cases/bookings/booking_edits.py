"""Small edits of a booking: its status and its notes."""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.bookings.status_undo import note_status_change
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES

# Target status -> statuses it may be reached from.
ALLOWED_TRANSITIONS: dict[BookingStatus, frozenset[BookingStatus]] = {
    BookingStatus.COMPLETED: BLOCKING_BOOKING_STATUSES,
    BookingStatus.NO_SHOW: BLOCKING_BOOKING_STATUSES,
    BookingStatus.CANCELLED: BLOCKING_BOOKING_STATUSES,
    BookingStatus.CONFIRMED: frozenset({BookingStatus.PENDING}),
}


def booking_unit_label(resource: ResourceDocument) -> str:
    return "nights" if resource.booking_unit is BookingUnit.NIGHT else "time slots"


def apply_status_change(
    booking: BookingDocument,
    status: BookingStatus | None,
    actor_id: UserId,
    now: Microseconds,
) -> bool:
    """
    Move the booking to `status` when that transition is allowed; the
    staff member (`actor_id`) may undo it for a short while.
    """

    if status is None or booking.status is status:
        return False

    allowed_from: frozenset[BookingStatus] = ALLOWED_TRANSITIONS.get(
        status, frozenset()
    )
    if booking.status not in allowed_from:
        raise ConflictError(f"A {booking.status} booking cannot become {status}.")

    note_status_change(booking, booking.status, actor_id, now)
    booking.status = status
    return True


def apply_notes_change(booking: BookingDocument, notes: BookingNote | None) -> bool:
    """Notes as given (the cabinet trims them); blank notes are removed."""

    if notes is None:
        return False

    new_notes: BookingNote | None = notes if str(notes).strip() else None
    if new_notes == booking.notes:
        return False

    booking.notes = new_notes
    return True
