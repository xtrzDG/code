"""The values of a saved reply's variables in one conversation."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.local_moments import format_local_moment

MICROSECONDS_PER_SECOND: int = 1_000_000
# A booking that still lies ahead: neither cancelled nor already over.
UPCOMING_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED}
)


def next_booking_start(
    bookings: Sequence[BookingDocument],
    now: Microseconds,
) -> BookingStartsAtUnixSeconds | None:
    """The start of the earliest pending or confirmed booking not begun yet."""

    now_seconds: int = int(now) // MICROSECONDS_PER_SECOND
    upcoming: list[BookingStartsAtUnixSeconds] = [
        booking.starts_at
        for booking in bookings
        if booking.status in UPCOMING_STATUSES and int(booking.starts_at) >= now_seconds
    ]
    return min(upcoming, key=int) if upcoming else None


def variable_values(
    business: BusinessDocument,
    contact: ContactDocument | None,
    booking_start: BookingStartsAtUnixSeconds | None,
    language: LanguageTag,
) -> dict[QuickReplyVariable, str]:
    """
    The values the conversation has: the customer's name when known, the
    next booking's start in the business time zone written in `language`,
    and the business name.
    """

    values: dict[QuickReplyVariable, str] = {
        QuickReplyVariable.BUSINESS_NAME: str(business.name)
    }
    if contact is not None and contact.name is not None:
        values[QuickReplyVariable.NAME] = str(contact.name)

    if booking_start is not None:
        values[QuickReplyVariable.BOOKING_TIME] = format_local_moment(
            int(booking_start), business.timezone, language
        )

    return values
