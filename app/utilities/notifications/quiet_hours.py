"""
Quiet hours of a staff recipient, in the business time zone: whether a
moment falls into them and when they end (across midnight when they end
earlier in the day than they start). DST gaps and repeats follow the
local wall clock (`lenient_utc_seconds`).
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.domain.notification_preferences import QuietHours
from app.utilities.scheduling.zoned_time import (
    lenient_utc_seconds,
    microseconds_to_seconds,
    minute_of_day,
    parse_time_of_day,
    to_local_moment,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


def is_valid_quiet_hours(quiet_hours: QuietHours) -> bool:
    """Quiet hours must have a length: start and end differ."""

    return parse_time_of_day(quiet_hours.starts_at) != parse_time_of_day(
        quiet_hours.ends_at
    )


def is_within(minute: int, starts: int, ends: int) -> bool:
    if starts < ends:
        return starts <= minute < ends

    return minute >= starts or minute < ends


def quiet_hours_end(
    quiet_hours: QuietHours | None,
    zone: ZoneInfo,
    now: Microseconds,
) -> Microseconds | None:
    """
    The moment the quiet hours around `now` end; None when `now` is outside
    them (or there are none).
    """

    if quiet_hours is None or not is_valid_quiet_hours(quiet_hours):
        return None

    starts: int = parse_time_of_day(quiet_hours.starts_at)
    ends: int = parse_time_of_day(quiet_hours.ends_at)
    local_now: datetime = to_local_moment(microseconds_to_seconds(int(now)), zone)
    minute: int = minute_of_day(local_now)
    if not is_within(minute, starts, ends):
        return None

    end_date: date = local_now.date()
    if minute >= ends:
        end_date += timedelta(days=1)

    end_seconds: int = lenient_utc_seconds(end_date, ends, zone)
    return Microseconds(max(end_seconds * MICROSECONDS_PER_SECOND, int(now)))
