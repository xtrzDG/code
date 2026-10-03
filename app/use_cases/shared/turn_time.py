"""Time arithmetic of a turn: business-local moments and windows."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.domain.businesses import BusinessDocument

MICROSECONDS_PER_SECOND: int = 1_000_000
UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)


def to_local_datetime(instant: Microseconds, business: BusinessDocument) -> datetime:
    """A UNIX instant as a wall-clock moment in the business time zone."""

    moment: datetime = UNIX_EPOCH + timedelta(microseconds=int(instant))
    return moment.astimezone(ZoneInfo(str(business.timezone)))


def to_microseconds(duration: timedelta) -> int:
    return int(duration.total_seconds() * MICROSECONDS_PER_SECOND)
