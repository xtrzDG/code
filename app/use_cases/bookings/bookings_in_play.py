"""The bookings a placement on a local date has to respect."""

from datetime import date
from zoneinfo import ZoneInfo

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    local_day_start_microseconds,
    microseconds_to_seconds,
)

# A booking that ended before the date can still block its first minutes
# with its buffer, so the read starts this much earlier.
LONGEST_BUFFER_SECONDS: int = (BufferMinutes.le or 0) * SECONDS_PER_MINUTE


def bookings_not_over_on(
    booking_repo: BookingRepoContract,
    business_id: BusinessId,
    local_date: date,
    zone: ZoneInfo,
) -> list[BookingDocument]:
    """
    Bookings that end after the local date begins (or whose buffer may
    still run then), by start time: every booking that can overlap a time
    on the date or a stay from it (one indexed range read, however many
    past bookings the business has).
    """

    day_start: int = microseconds_to_seconds(
        local_day_start_microseconds(local_date, zone)
    )
    return booking_repo.list_ending_after(
        business_id,
        BookingSearchBoundSeconds(max(day_start - LONGEST_BUFFER_SECONDS, 0)),
    )
