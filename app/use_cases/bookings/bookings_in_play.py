"""The bookings and held places a placement on a local date respects."""

from datetime import date
from typing import NamedTuple
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    local_day_start_microseconds,
    microseconds_to_seconds,
)

# A booking that ended before the date can still block its first minutes
# with its buffer, so the read starts this much earlier.
LONGEST_BUFFER_SECONDS: int = (BufferMinutes.le or 0) * SECONDS_PER_MINUTE


class HeldPlaces(NamedTuple):
    """
    The places held for waiting customers at `now` that a placement must
    respect: every one but those held for `holder`, who may take theirs.
    """

    growth: GrowthBookingsFacilitatorContract
    now: Microseconds
    holder: ContactId | None = None


def bookings_not_over_on(
    booking_repo: BookingRepoContract,
    business_id: BusinessId,
    local_date: date,
    zone: ZoneInfo,
    held: HeldPlaces,
) -> list[BookingDocument]:
    """
    Bookings that end after the local date begins (or whose buffer may
    still run then), by start time: every booking that can overlap a time
    on the date or a stay from it (one indexed range read, however many
    past bookings the business has), with the waitlist's live holds as
    unsaved bookings of their places.
    """

    day_start: int = microseconds_to_seconds(
        local_day_start_microseconds(local_date, zone)
    )
    bound = BookingSearchBoundSeconds(max(day_start - LONGEST_BUFFER_SECONDS, 0))
    bookings: list[BookingDocument] = booking_repo.list_ending_after(business_id, bound)
    places: list[BookingDocument] = held.growth.held_places(
        business_id, bound, held.now, held.holder
    )
    if not places:
        return bookings

    return sorted([*bookings, *places], key=lambda booking: int(booking.starts_at))
