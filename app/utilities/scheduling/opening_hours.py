"""Effective opening ranges of a business or a resource on a local date.

Weekly hours come from the resource schedule or the business profile.
Schedule exceptions override them for one date: closed all day, or special
hours. A range whose closing minute is not after its opening minute runs
overnight into the next day (Fri 18:00-02:00).

Precedence for a resource on a date:
1. a resource-level exception for the date (closed, or its special hours);
2. a business-level exception: closed closes everything; special hours
   replace business hours, or are intersected with the resource's own
   schedule when it has one;
3. the weekly hours (resource schedule, else business hours).

An exception that is not closed and has no special hours keeps the weekly
hours (it only carries a note).
"""

from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.utilities.scheduling.zoned_time import (
    MINUTES_PER_DAY,
    iso_weekday,
    lenient_utc_seconds,
    to_local_date,
    to_local_moment,
)

DEFAULT_OPENING_SEARCH_DAYS: int = 14


class MinuteRange(NamedTuple):
    """
    Opening range in wall minutes from local midnight of a reference date.

    `end` may pass 1440 (overnight) and `start` may be negative (a range that
    began the previous evening).
    """

    start: int
    end: int


type DayRanges = Callable[[date], list[MinuteRange]]


def to_minute_range(interval: OpeningInterval) -> MinuteRange:
    opens_at: int = int(interval.opens_at)
    closes_at: int = int(interval.closes_at)
    if closes_at <= opens_at:
        closes_at += MINUTES_PER_DAY

    return MinuteRange(opens_at, closes_at)


def weekly_ranges(
    schedule: Sequence[OpeningInterval],
    weekday: Weekday,
) -> list[MinuteRange]:
    """Ranges of the weekly schedule that start on the weekday."""

    return merge_ranges(
        [
            to_minute_range(interval)
            for interval in schedule
            if interval.weekday is weekday
        ]
    )


def special_ranges(special_hours: Sequence[OpeningInterval]) -> list[MinuteRange]:
    """Special hours of one exception date; their weekday field is ignored."""

    return merge_ranges([to_minute_range(interval) for interval in special_hours])


def merge_ranges(ranges: Sequence[MinuteRange]) -> list[MinuteRange]:
    """Sort ranges and merge the ones that overlap or touch."""

    merged: list[MinuteRange] = []
    for current in sorted(ranges):
        if merged and current.start <= merged[-1].end:
            previous: MinuteRange = merged[-1]
            merged[-1] = MinuteRange(previous.start, max(previous.end, current.end))
        else:
            merged.append(current)

    return merged


def intersect_ranges(
    first: Sequence[MinuteRange],
    second: Sequence[MinuteRange],
) -> list[MinuteRange]:
    intersections: list[MinuteRange] = []
    for left in first:
        for right in second:
            start: int = max(left.start, right.start)
            end: int = min(left.end, right.end)
            if start < end:
                intersections.append(MinuteRange(start, end))

    return merge_ranges(intersections)


def find_exception(
    exceptions: Sequence[ScheduleExceptionDocument],
    local_date: date,
    resource_id: ResourceId | None,
) -> ScheduleExceptionDocument | None:
    """The exception for the date at business level (None) or for a resource."""

    date_key = to_local_date(local_date)
    for exception in exceptions:
        if exception.date == date_key and exception.resource_id == resource_id:
            return exception

    return None


def apply_exception(
    regular: list[MinuteRange],
    exception: ScheduleExceptionDocument | None,
) -> list[MinuteRange]:
    if exception is None:
        return regular

    if exception.is_closed_all_day:
        return []

    if exception.special_hours:
        return special_ranges(exception.special_hours)

    return regular


def business_ranges_starting_on(
    local_date: date,
    business_hours: Sequence[OpeningInterval],
    exceptions: Sequence[ScheduleExceptionDocument],
) -> list[MinuteRange]:
    """Business opening ranges that start on the date."""

    regular: list[MinuteRange] = weekly_ranges(business_hours, iso_weekday(local_date))
    return apply_exception(regular, find_exception(exceptions, local_date, None))


def business_day_ranges(
    business_hours: Sequence[OpeningInterval],
    exceptions: Sequence[ScheduleExceptionDocument],
) -> DayRanges:
    """Business opening ranges starting on any given date."""

    weekly_hours: list[OpeningInterval] = list(business_hours)
    exception_days: list[ScheduleExceptionDocument] = list(exceptions)

    def ranges_starting_on(local_date: date) -> list[MinuteRange]:
        return business_ranges_starting_on(local_date, weekly_hours, exception_days)

    return ranges_starting_on


def resource_ranges_starting_on(
    local_date: date,
    resource_id: ResourceId,
    resource_schedule: Sequence[OpeningInterval],
    business_hours: Sequence[OpeningInterval],
    exceptions: Sequence[ScheduleExceptionDocument],
) -> list[MinuteRange]:
    """Opening ranges of a resource that start on the date (module docstring)."""

    weekday: Weekday = iso_weekday(local_date)
    own_schedule: Sequence[OpeningInterval] = resource_schedule or business_hours
    resource_exception: ScheduleExceptionDocument | None = find_exception(
        exceptions, local_date, resource_id
    )
    if resource_exception is not None:
        return apply_exception(weekly_ranges(own_schedule, weekday), resource_exception)

    if not resource_schedule:
        return business_ranges_starting_on(local_date, business_hours, exceptions)

    own_ranges: list[MinuteRange] = weekly_ranges(resource_schedule, weekday)
    business_exception: ScheduleExceptionDocument | None = find_exception(
        exceptions, local_date, None
    )
    if business_exception is None:
        return own_ranges

    if business_exception.is_closed_all_day:
        return []

    if business_exception.special_hours:
        return intersect_ranges(
            own_ranges, special_ranges(business_exception.special_hours)
        )

    return own_ranges


def ranges_around(local_date: date, ranges_starting_on: DayRanges) -> list[MinuteRange]:
    """
    Ranges that touch the date, relative to its midnight: the previous day's
    overnight ranges (shifted by one day) and the ranges starting on the date.
    """

    previous_date: date = local_date - timedelta(days=1)
    shifted: list[MinuteRange] = [
        MinuteRange(previous.start - MINUTES_PER_DAY, previous.end - MINUTES_PER_DAY)
        for previous in ranges_starting_on(previous_date)
        if previous.end > MINUTES_PER_DAY
    ]
    return merge_ranges(shifted + ranges_starting_on(local_date))


def is_open_on_date(local_date: date, ranges_starting_on: DayRanges) -> bool:
    """True when some opening range covers part of the date."""

    return any(
        opening.start < MINUTES_PER_DAY and opening.end > 0
        for opening in ranges_around(local_date, ranges_starting_on)
    )


def is_open_at(utc_seconds: int, zone: ZoneInfo, ranges_starting_on: DayRanges) -> bool:
    """True when the moment falls inside an opening range."""

    local_date: date = to_local_moment(utc_seconds, zone).date()
    for opening in ranges_around(local_date, ranges_starting_on):
        opens_at: int = lenient_utc_seconds(local_date, opening.start, zone)
        closes_at: int = lenient_utc_seconds(local_date, opening.end, zone)
        if opens_at <= utc_seconds < closes_at:
            return True

    return False


def find_next_opening(
    utc_seconds: int,
    zone: ZoneInfo,
    ranges_starting_on: DayRanges,
    search_days: int = DEFAULT_OPENING_SEARCH_DAYS,
) -> datetime | None:
    """Local moment of the first opening strictly after the moment, if any."""

    first_date: date = to_local_moment(utc_seconds, zone).date()
    for day_offset in range(search_days + 1):
        local_date: date = first_date + timedelta(days=day_offset)
        for opening in ranges_starting_on(local_date):
            opens_at: int = lenient_utc_seconds(local_date, opening.start, zone)
            if opens_at > utc_seconds:
                return to_local_moment(opens_at, zone)

    return None
