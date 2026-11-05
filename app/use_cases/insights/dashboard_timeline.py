"""
The dashboard period as a timeline the database counts by: every local
day, split into the stretches when the business is open and closed.

Conversations count as after hours when the conversation engine flagged
them or when they started while the business was closed by its weekly
hours with the exceptions applied (`is_open_at`, to the second). Counting
by these stretches gives the same answer without reading a conversation:
one grouped count per stretch (`ActivityPeriod`).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.dto.operations.activity_counts import ActivityPeriod
from app.utilities.scheduling.opening_hours import (
    DayRanges,
    MinuteRange,
    ranges_around,
)
from app.utilities.scheduling.zoned_time import (
    MICROSECONDS_PER_SECOND,
    lenient_utc_seconds,
    local_day_start_microseconds,
)


@dataclass(frozen=True)
class TimelineStretch:
    """From `start` (UTC microseconds) to the next stretch, on one local day."""

    start: int
    day: int
    is_open: bool


def build_timeline(
    date_from: date,
    date_to: date,
    zone: ZoneInfo,
    ranges_starting_on: DayRanges | None,
) -> list[TimelineStretch]:
    """
    Stretches of every local date from `date_from` to `date_to`: one per day
    without weekly hours, else the open and closed parts of each day.
    """

    stretches: list[TimelineStretch] = []
    for day in range((date_to - date_from).days + 1):
        local_date: date = date_from + timedelta(days=day)
        day_start: int = local_day_start_microseconds(local_date, zone)
        next_day: int = local_day_start_microseconds(
            local_date + timedelta(days=1), zone
        )
        if ranges_starting_on is None:
            stretches.append(TimelineStretch(start=day_start, day=day, is_open=True))
            continue

        position: int = day_start
        for opens, closes in open_intervals(
            local_date, zone, ranges_starting_on, day_start, next_day
        ):
            if opens > position:
                stretches.append(
                    TimelineStretch(start=position, day=day, is_open=False)
                )
            stretches.append(TimelineStretch(start=opens, day=day, is_open=True))
            position = closes

        if position < next_day:
            stretches.append(TimelineStretch(start=position, day=day, is_open=False))

    return stretches


def open_intervals(
    local_date: date,
    zone: ZoneInfo,
    ranges_starting_on: DayRanges,
    day_start: int,
    next_day: int,
) -> list[tuple[int, int]]:
    """When the business is open on the date (UTC microseconds), merged."""

    clipped: list[tuple[int, int]] = []
    for opening in ranges_around(local_date, ranges_starting_on):
        opens: int = max(utc_microseconds(local_date, opening, zone, True), day_start)
        closes: int = min(utc_microseconds(local_date, opening, zone, False), next_day)
        if opens < closes:
            clipped.append((opens, closes))

    merged: list[tuple[int, int]] = []
    for opens, closes in sorted(clipped):
        if merged and opens <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], closes))
        else:
            merged.append((opens, closes))

    return merged


def utc_microseconds(
    local_date: date, opening: MinuteRange, zone: ZoneInfo, is_start: bool
) -> int:
    minute: int = opening.start if is_start else opening.end
    return lenient_utc_seconds(local_date, minute, zone) * MICROSECONDS_PER_SECOND


def timeline_period(stretches: list[TimelineStretch], end: int) -> ActivityPeriod:
    """The period the stretches cover, one segment per stretch."""

    return ActivityPeriod(
        start=Microseconds(stretches[0].start),
        end=Microseconds(end),
        segment_starts=tuple(Microseconds(stretch.start) for stretch in stretches),
    )
