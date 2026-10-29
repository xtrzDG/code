"""Why a booking could not be placed, as an error with a reason code."""

from collections.abc import Sequence
from datetime import date

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.utilities.scheduling.zoned_time import to_local_date

FAILURE_CLOSED: str = "closed"
FAILURE_TOO_SOON: str = "too_soon"
FAILURE_TAKEN: str = "taken"
FAILURE_TIME_REQUIRED: str = "time_required"


def booking_refusal_reason(
    code: BookingRefusalCode,
    message: str,
    details: Sequence[str] = (),
) -> ErrorReason:
    """The machine-readable reason of a booking refusal (with its English text)."""

    return ErrorReason(
        code=ErrorReasonCode(code.value),
        message=ErrorReasonMessage(message),
        details=[ErrorReasonDetail(detail) for detail in details],
    )


def placement_error(failures: set[str], local_date: date) -> Exception:
    """
    The most useful error for the caller: taken, too soon, no time, closed.
    Each carries a reason code (with the day where it matters), so the
    cabinet can explain it in the user's language.
    """

    day: str = str(to_local_date(local_date))
    message: str
    if FAILURE_TAKEN in failures:
        message = (
            f"That time on {day} is already booked. Check availability for "
            "another time."
        )
        return ConflictError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.TAKEN, message, [day])],
        )

    if FAILURE_TOO_SOON in failures:
        message = "That time is too soon: bookings need more advance notice."
        return ValidationFailedError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.TOO_SOON, message)],
        )

    if FAILURE_TIME_REQUIRED in failures:
        message = "A time is required for this booking."
        return ValidationFailedError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.TIME_REQUIRED, message)],
        )

    if failures:
        message = (
            f"The business is closed at that time on {day} (outside opening hours "
            "or a holiday)."
        )
        return ValidationFailedError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.CLOSED, message, [day])],
        )

    message = "No bookable resource seats a party of this size."
    return ValidationFailedError(
        message,
        reasons=[
            booking_refusal_reason(BookingRefusalCode.NO_SEATING_RESOURCE, message)
        ],
    )
