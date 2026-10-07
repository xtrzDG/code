"""
A guest's manage link changes a booking only as it was when the link was
issued: its start time is the version, checked under the business lock.
The cabinet's calendar moves a booking only from the local start it
showed.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import ManagedBookingRefusalCode
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.utilities.scheduling.zoned_time import (
    minute_of_day,
    to_local_date,
    to_local_moment,
    to_time_of_day,
)

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


MOVED_MESSAGE: str = (
    "The booking was moved after the calendar showed it; look at its new time."
)


def refuse_moved_booking(
    booking: BookingDocument,
    zone: ZoneInfo,
    expected_date: LocalDate | None,
    expected_time: LocalTimeOfDay | None,
) -> None:
    """
    The cabinet's version of a booking: its local start date (and time)
    as the calendar showed it.

    Raises:
        ConflictError: the booking starts at another local date or time
            now (reason `booking_changed`).
    """

    if expected_date is None:
        return

    starts: datetime = to_local_moment(int(booking.starts_at), zone)
    if to_local_date(starts.date()) == expected_date and (
        expected_time is None or to_time_of_day(minute_of_day(starts)) == expected_time
    ):
        return

    raise ConflictError(
        MOVED_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(ManagedBookingRefusalCode.BOOKING_CHANGED.value),
                message=ErrorReasonMessage(MOVED_MESSAGE),
            )
        ],
    )
