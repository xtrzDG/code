"""IANA time zones: known names, per-country lists and display names."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import cast
from zoneinfo import ZoneInfo, available_timezones

from babel.core import get_global
from typed_time_provider import Microseconds

from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.localization.strings import TimezoneDisplayName

UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
SECONDS_IN_MINUTE: int = 60
MINUTES_IN_HOUR: int = 60


def is_known_timezone_name(timezone_name: str) -> bool:
    """True when the IANA database installed here has exactly this name."""

    return timezone_name in load_available_timezone_names()


def list_territory_timezone_names(region_code: str) -> list[TimezoneName]:
    """
    Time zones CLDR lists for a region that the IANA database also has.

    Returned in alphabetical order; empty for regions CLDR does not map
    (for example Ascension Island or Kosovo).
    """

    territory_zones: object = get_global("territory_zones").get(region_code)
    if not isinstance(territory_zones, list | tuple):
        return []

    zone_candidates: Sequence[object] = cast(Sequence[object], territory_zones)
    zone_names: list[str] = sorted(
        {
            zone_name
            for zone_name in zone_candidates
            if isinstance(zone_name, str) and is_known_timezone_name(zone_name)
        }
    )
    return [TimezoneName(zone_name) for zone_name in zone_names]


def build_timezone_display_name(
    timezone_name: TimezoneName,
    instant: Microseconds,
) -> TimezoneDisplayName:
    """
    Name with the UTC offset in force at an instant: "Asia/Tbilisi (UTC+04:00)".

    The offset follows daylight saving time, so "Europe/Warsaw" reads
    UTC+02:00 in July and UTC+01:00 in January.
    """

    offset: timedelta = compute_utc_offset(timezone_name, instant)
    return TimezoneDisplayName(f"{timezone_name} (UTC{format_utc_offset(offset)})")


def compute_utc_offset(timezone_name: TimezoneName, instant: Microseconds) -> timedelta:
    """UTC offset of a time zone at a UNIX instant in microseconds."""

    moment: datetime = UNIX_EPOCH + timedelta(microseconds=int(instant))
    offset: timedelta | None = moment.astimezone(
        ZoneInfo(str(timezone_name))
    ).utcoffset()
    return offset if offset is not None else timedelta(0)


def format_utc_offset(offset: timedelta) -> str:
    """Offset as "+HH:MM" or "-HH:MM" (seconds are dropped)."""

    total_seconds: int = int(offset.total_seconds())
    sign: str = "-" if total_seconds < 0 else "+"
    total_minutes: int = abs(total_seconds) // SECONDS_IN_MINUTE
    hours, minutes = divmod(total_minutes, MINUTES_IN_HOUR)
    return f"{sign}{hours:02d}:{minutes:02d}"


@cache
def load_available_timezone_names() -> frozenset[str]:
    """Every IANA name this process can load with zoneinfo."""

    return frozenset(available_timezones())
