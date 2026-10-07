"""Moments as the public API writes them (ISO 8601 with seconds and offset)."""

from datetime import UTC, datetime

from typed_time_provider import Microseconds

from app.schemas.typings.integrations.constrained_strings import PublicTimestamp
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000


def utc_timestamp(moment: Microseconds) -> PublicTimestamp:
    """`2026-10-06T15:30:00Z`: a moment in UTC, whole seconds."""

    when = datetime.fromtimestamp(int(moment) // MICROSECONDS_PER_SECOND, UTC)
    return PublicTimestamp(when.strftime("%Y-%m-%dT%H:%M:%SZ"))


def local_timestamp(unix_seconds: int, timezone: TimezoneName) -> PublicTimestamp:
    """`2026-10-06T19:30:00+04:00`: a moment with the business's offset."""

    when = datetime.fromtimestamp(unix_seconds, load_time_zone(timezone))
    return PublicTimestamp(when.isoformat(timespec="seconds"))
