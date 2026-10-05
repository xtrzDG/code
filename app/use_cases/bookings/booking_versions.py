"""
A guest's manage link changes a booking only as it was when the link was
issued: its start time is the version, checked under the business lock.
"""

from app.schemas.constants.bookings import ManagedBookingRefusalCode
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

CHANGED_MESSAGE: str = (
    "The booking was changed after this link was sent; open the latest confirmation."
)


def refuse_changed_booking(
    booking: BookingDocument,
    expected_starts_at: BookingStartsAtUnixSeconds | None,
) -> None:
    """
    Raises:
        ConflictError: the booking no longer starts when the caller saw it
            (reason `booking_changed`).
    """

    if expected_starts_at is None or booking.starts_at == expected_starts_at:
        return

    raise ConflictError(
        CHANGED_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(ManagedBookingRefusalCode.BOOKING_CHANGED.value),
                message=ErrorReasonMessage(CHANGED_MESSAGE),
            )
        ],
    )
