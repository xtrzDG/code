"""
Marketing never reaches a customer at night (Garante's guidance on
marketing messages; the customers' rest): a campaign writes only from 09:00
to 21:00 in its business's time zone, and a message the outbox could not
deliver before 21:00 is dropped rather than delivered late at night.
Service messages (confirmations, reminders, a deposit's line) are other
flows and are not held.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

MICROSECONDS_PER_SECOND: int = 1_000_000
# Local hours of the business: no marketing from 21:00 until 09:00.
QUIET_FROM: time = time(21, 0)
QUIET_UNTIL: time = time(9, 0)


def local_moment(now: Microseconds, zone: ZoneInfo) -> datetime:
    return datetime.fromtimestamp(int(now) / MICROSECONDS_PER_SECOND, zone)


def is_quiet_hour(now: Microseconds, zone: ZoneInfo) -> bool:
    """True from 21:00 until 09:00 in the business's time zone."""

    local: time = local_moment(now, zone).time()
    return local >= QUIET_FROM or local < QUIET_UNTIL


def quiet_hours_start(now: Microseconds, zone: ZoneInfo) -> Microseconds:
    """
    When the next quiet hours begin: today's 21:00 in the business's time
    zone, or tomorrow's once 21:00 has passed.
    """

    local: datetime = local_moment(now, zone)
    start: datetime = datetime.combine(local.date(), QUIET_FROM, tzinfo=zone)
    if start <= local:
        start = datetime.combine(
            local.date() + timedelta(days=1), QUIET_FROM, tzinfo=zone
        )

    return Microseconds(int(start.timestamp()) * MICROSECONDS_PER_SECOND)
