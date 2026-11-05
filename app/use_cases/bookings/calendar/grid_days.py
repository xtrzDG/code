"""
How full each place is on each day of a calendar window: the opening
ranges of a place booked by time slots and the unit-minutes its bookings
fill within them, or the rooms of a place booked by the night that are
for sale and taken that night. Cancelled bookings never come here.
"""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.booking_grid import (
    BookingGridDay,
    BookingGridPlaceDay,
    GridOpenRange,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookedUnitCount,
    BookedUnitMinutes,
    GridBookingCount,
    OpenUnitCount,
    OpenUnitMinutes,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.utilities.scheduling.availability import (
    is_date_closed_for_stays,
    resource_day_ranges,
)
from app.utilities.scheduling.opening_hours import (
    MinuteRange,
    business_day_ranges,
    ranges_around,
)
from app.utilities.scheduling.zoned_time import (
    MINUTES_PER_DAY,
    SECONDS_PER_MINUTE,
    lenient_utc_seconds,
    to_local_date,
    to_local_moment,
)


class GridHours(NamedTuple):
    """What the opening hours of a day depend on."""

    zone: ZoneInfo
    business_hours: Sequence[OpeningInterval]
    exceptions: Sequence[ScheduleExceptionDocument]


def grid_day(
    local_date: date,
    places: Sequence[ResourceDocument],
    bookings_by_place: dict[ResourceId, list[BookingDocument]],
    hours: GridHours,
) -> BookingGridDay:
    """The business's ranges of the day and every place on it."""

    return BookingGridDay(
        date=to_local_date(local_date),
        business_ranges=_within_day(
            ranges_around(
                local_date, business_day_ranges(hours.business_hours, hours.exceptions)
            )
        ),
        places=[
            (
                _night_place_day(
                    local_date, place, bookings_by_place.get(place.id, []), hours
                )
                if place.booking_unit is BookingUnit.NIGHT
                else _slot_place_day(
                    local_date, place, bookings_by_place.get(place.id, []), hours
                )
            )
            for place in places
        ],
    )


def _slot_place_day(
    local_date: date,
    place: ResourceDocument,
    bookings: Sequence[BookingDocument],
    hours: GridHours,
) -> BookingGridPlaceDay:
    ranges: list[GridOpenRange] = _within_day(
        ranges_around(
            local_date,
            resource_day_ranges(place, hours.business_hours, hours.exceptions),
        )
    )
    spans: list[tuple[int, int]] = [
        (
            lenient_utc_seconds(local_date, int(opening.opens_at), hours.zone),
            lenient_utc_seconds(local_date, int(opening.closes_at), hours.zone),
        )
        for opening in ranges
    ]
    day_start: int = lenient_utc_seconds(local_date, 0, hours.zone)
    day_end: int = lenient_utc_seconds(local_date, MINUTES_PER_DAY, hours.zone)
    on_day: list[BookingDocument] = [
        booking for booking in bookings if _overlap(booking, day_start, day_end) > 0
    ]
    open_minutes: int = sum((end - start) // SECONDS_PER_MINUTE for start, end in spans)
    open_unit_minutes: int = open_minutes * int(place.unit_count)
    booked_seconds: int = sum(
        _overlap(booking, start, end) for booking in on_day for start, end in spans
    )
    return BookingGridPlaceDay(
        resource_id=place.id,
        is_open=bool(ranges),
        open_ranges=ranges,
        booking_count=GridBookingCount(len(on_day)),
        open_unit_minutes=OpenUnitMinutes(open_unit_minutes),
        booked_unit_minutes=BookedUnitMinutes(
            min(booked_seconds // SECONDS_PER_MINUTE, open_unit_minutes)
        ),
    )


def _night_place_day(
    local_date: date,
    place: ResourceDocument,
    bookings: Sequence[BookingDocument],
    hours: GridHours,
) -> BookingGridPlaceDay:
    is_closed: bool = is_date_closed_for_stays(local_date, place, hours.exceptions)
    staying: int = sum(
        1
        for booking in bookings
        if to_local_moment(int(booking.starts_at), hours.zone).date()
        <= local_date
        < to_local_moment(int(booking.ends_at), hours.zone).date()
    )
    return BookingGridPlaceDay(
        resource_id=place.id,
        is_open=not is_closed,
        booking_count=GridBookingCount(staying),
        open_units=OpenUnitCount(0 if is_closed else int(place.unit_count)),
        booked_units=BookedUnitCount(min(staying, int(BookedUnitCount.le or staying))),
    )


def _within_day(ranges: Sequence[MinuteRange]) -> list[GridOpenRange]:
    """Opening ranges cut to the day itself (an overnight range shows on both days)."""

    within: list[GridOpenRange] = []
    for opening in ranges:
        start: int = max(opening.start, 0)
        end: int = min(opening.end, MINUTES_PER_DAY)
        if end > start:
            within.append(
                GridOpenRange(
                    opens_at=OpeningMinuteOfDay(start),
                    closes_at=ClosingMinuteOfDay(end),
                )
            )

    return within


def _overlap(booking: BookingDocument, start: int, end: int) -> int:
    """Seconds of the booking within [start, end)."""

    return max(min(int(booking.ends_at), end) - max(int(booking.starts_at), start), 0)
