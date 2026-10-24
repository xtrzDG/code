"""The day spend is counted for: a business's own, or the platform's UTC day."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
DAY_MICROSECONDS: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND


def day_start(now: Microseconds, zone: ZoneInfo) -> tuple[SpendDay, Microseconds]:
    """The calendar day in `zone` that holds `now`, and when it began (UTC)."""

    local: datetime = datetime.fromtimestamp(
        int(now) // MICROSECONDS_PER_SECOND, tz=UTC
    ).astimezone(zone)
    midnight: datetime = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        SpendDay(local.date().isoformat()),
        Microseconds(int(midnight.timestamp()) * MICROSECONDS_PER_SECOND),
    )


def business_day(
    now: Microseconds, timezone: TimezoneName
) -> tuple[SpendDay, Microseconds]:
    """A business's own day (its time zone): its daily limits reset at midnight."""

    return day_start(now, load_time_zone(timezone))


def utc_day(now: Microseconds) -> tuple[SpendDay, Microseconds]:
    """The platform's day (UTC): its spend tile, budget and spike alert."""

    return day_start(now, ZoneInfo("UTC"))


def days_before(start: Microseconds, days: int) -> Microseconds:
    """The moment `days` whole days before `start` (UTC days have no DST)."""

    return Microseconds(int(start) - days * DAY_MICROSECONDS)
