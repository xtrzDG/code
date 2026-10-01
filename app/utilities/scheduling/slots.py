"""Time slots inside opening ranges, computed in wall time and checked in UTC.

Slot starts step by min(duration, 30) minutes from the opening of each range.
A slot must fit fully inside one (merged) opening range, measured in real
elapsed time, so daylight-saving days are handled: starts skipped by a jump
forward are left out, and ambiguous starts use their first occurrence.
"""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.utilities.scheduling.opening_hours import MinuteRange
from app.utilities.scheduling.zoned_time import (
    MINUTES_PER_DAY,
    SECONDS_PER_MINUTE,
    find_utc_seconds,
    lenient_utc_seconds,
    require_utc_seconds,
)

MAX_SLOT_STEP_MINUTES: int = 30


class TimeSlot(NamedTuple):
    """A slot starting on a local date: wall minute of the start and UTC bounds."""

    minute_of_day: int
    starts_at: int
    ends_at: int


def slot_step_minutes(duration_minutes: int) -> int:
    return min(duration_minutes, MAX_SLOT_STEP_MINUTES)


def generate_slots(
    local_date: date,
    zone: ZoneInfo,
    day_ranges: Sequence[MinuteRange],
    duration_minutes: int,
) -> list[TimeSlot]:
    """
    Every slot of `duration_minutes` that starts on the date and fits an
    opening range. `day_ranges` are relative to the date's midnight (see
    `ranges_around`).
    """

    step: int = slot_step_minutes(duration_minutes)
    slots_by_minute: dict[int, TimeSlot] = {}
    for opening in day_ranges:
        opens_at: int = lenient_utc_seconds(local_date, opening.start, zone)
        closes_at: int = lenient_utc_seconds(local_date, opening.end, zone)
        first_minute: int = opening.start
        if first_minute < 0:
            first_minute += -(first_minute // step) * step

        for minute in range(first_minute, min(opening.end, MINUTES_PER_DAY), step):
            starts_at: int | None = find_utc_seconds(local_date, minute, zone)
            if starts_at is None:
                continue

            ends_at: int = starts_at + duration_minutes * SECONDS_PER_MINUTE
            if starts_at < opens_at or ends_at > closes_at:
                continue

            slots_by_minute.setdefault(minute, TimeSlot(minute, starts_at, ends_at))

    return [slots_by_minute[minute] for minute in sorted(slots_by_minute)]


def fit_slot(
    local_date: date,
    minute_of_day: int,
    zone: ZoneInfo,
    day_ranges: Sequence[MinuteRange],
    duration_minutes: int,
) -> TimeSlot | None:
    """
    The slot at an exact wall time when it fits an opening range, else None.

    Raises ValidationFailedError when the wall time is skipped by a
    daylight-saving jump.
    """

    starts_at: int = require_utc_seconds(local_date, minute_of_day, zone)
    ends_at: int = starts_at + duration_minutes * SECONDS_PER_MINUTE
    for opening in day_ranges:
        opens_at: int = lenient_utc_seconds(local_date, opening.start, zone)
        closes_at: int = lenient_utc_seconds(local_date, opening.end, zone)
        if opens_at <= starts_at and ends_at <= closes_at:
            return TimeSlot(minute_of_day, starts_at, ends_at)

    return None


def nearest_minutes(
    minutes: Sequence[int], target_minute: int, limit: int
) -> list[int]:
    """Up to `limit` wall minutes nearest to the target, in time order."""

    by_distance: list[int] = sorted(
        minutes,
        key=lambda minute: (abs(minute - target_minute), minute),
    )
    return sorted(by_distance[:limit])
