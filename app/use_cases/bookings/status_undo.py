"""Staff's last status change of a booking, and what undoing it requires."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, BookingUndoRefusalCode
from app.schemas.domain.bookings import BookingDocument, BookingStatusChange
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.scheduling.availability import (
    BLOCKING_BOOKING_STATUSES,
    blocked_until,
    busy_ranges,
)
from app.utilities.scheduling.overlap import has_free_unit

# How long after a status change staff may undo it.
UNDO_WINDOW_SECONDS: int = 10 * 60
MICROSECONDS_PER_SECOND: int = 1_000_000


def note_status_change(
    booking: BookingDocument,
    previous_status: BookingStatus,
    actor_id: UserId | None,
    now: Microseconds,
) -> None:
    """
    Keep a change staff made in the cabinet (`actor_id`) for an Undo. A
    change by anyone else (the customer cancelling through the assistant)
    cannot be undone by staff, and leaves no earlier change to undo.
    """

    booking.last_status_change = (
        None
        if actor_id is None
        else BookingStatusChange(
            previous_status=previous_status, changed_at=now, changed_by=actor_id
        )
    )


def require_undoable(
    booking: BookingDocument,
    undone_status: BookingStatus,
    now: Microseconds,
) -> BookingStatusChange:
    """
    The change an Undo restores: staff made it, the booking still has the
    status it set (`undone_status`), and it is at most UNDO_WINDOW_SECONDS
    old.

    Raises:
        ConflictError: with the reason (nothing_to_undo, status_changed,
            undo_expired).
    """

    change: BookingStatusChange | None = booking.last_status_change
    if change is None:
        raise undo_refusal(
            BookingUndoRefusalCode.NOTHING_TO_UNDO,
            "This booking has no status change to undo.",
        )

    if booking.status is not undone_status:
        raise undo_refusal(
            BookingUndoRefusalCode.STATUS_CHANGED,
            f"The booking is {booking.status} now, not {undone_status}.",
            [booking.status.value],
        )

    age_seconds: int = (int(now) - int(change.changed_at)) // MICROSECONDS_PER_SECOND
    if age_seconds > UNDO_WINDOW_SECONDS:
        raise undo_refusal(
            BookingUndoRefusalCode.UNDO_EXPIRED,
            f"A status change can be undone for {UNDO_WINDOW_SECONDS // 60} "
            "minutes only.",
            [str(UNDO_WINDOW_SECONDS // 60)],
        )

    return change


def takes_time_again(booking: BookingDocument, change: BookingStatusChange) -> bool:
    """Whether the Undo makes a booking that freed its time hold it again."""

    return (
        booking.status not in BLOCKING_BOOKING_STATUSES
        and change.previous_status in BLOCKING_BOOKING_STATUSES
    )


def ensure_time_still_free(
    booking: BookingDocument,
    resource: ResourceDocument | None,
    bookings_in_play: Sequence[BookingDocument],
) -> None:
    """
    A unit of the booking's place is free again for its whole time and
    buffer, as the full-day availability counts it (staff rules: no
    notice; the booking itself not counted; a test booking sees real
    ones and its own conversation's).

    Raises:
        ConflictError: the place is gone (place_gone) or another booking
            took the time in the meantime (slot_taken, with the place's id).
    """

    if resource is None:
        raise undo_refusal(
            BookingUndoRefusalCode.PLACE_GONE,
            "The booking's place no longer exists; make a new booking instead.",
        )

    busy = busy_ranges(
        bookings_in_play,
        resource,
        booking.is_sandbox,
        booking.id,
        booking.conversation_id if booking.is_sandbox else None,
    )
    if not has_free_unit(
        busy,
        int(booking.starts_at),
        blocked_until(booking),
        int(resource.unit_count),
    ):
        raise undo_refusal(
            BookingUndoRefusalCode.SLOT_TAKEN,
            f"{resource.name} was booked by someone else for this time in the "
            "meantime.",
            [str(resource.id)],
        )


def undo_refusal(
    code: BookingUndoRefusalCode,
    message: str,
    details: Sequence[str] = (),
) -> ConflictError:
    return ConflictError(
        message,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(code.value),
                message=ErrorReasonMessage(message),
                details=[ErrorReasonDetail(detail) for detail in details],
            )
        ],
    )
