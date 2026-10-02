"""The bookings a placement on a local date has to respect."""

from datetime import date
from zoneinfo import ZoneInfo

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.scheduling.zoned_time import (
    local_day_start_microseconds,
    microseconds_to_seconds,
)


def bookings_not_over_on(
    booking_repo: BookingRepoContract,
    business_id: BusinessId,
    local_date: date,
    zone: ZoneInfo,
) -> list[BookingDocument]:
    """
    Bookings that end after the local date begins, by start time: every
    booking that can overlap a time on the date or a stay from it (one
    indexed range read, however many past bookings the business has).
    """

    day_start: int = microseconds_to_seconds(
        local_day_start_microseconds(local_date, zone)
    )
    return booking_repo.list_ending_after(
        business_id, BookingSearchBoundSeconds(max(day_start, 0))
    )
