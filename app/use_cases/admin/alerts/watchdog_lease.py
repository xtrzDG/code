"""
Which API process leads the pipeline watchdog. The lease lives in the
watchdog's mark (`platform_monitors`) and is read and renewed only under
the alert-state lock, so two processes never both lead: the holder renews
it on every look; another process takes it once it ran out (the leader
died, stalled, or was stopped by a deploy).
"""

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformMonitor
from app.schemas.domain.platform_monitors import PlatformMonitorDocument
from app.schemas.typings.monitoring.constrained_integers import (
    PipelineWatchdogSeconds,
)
from app.schemas.typings.monitoring.constrained_strings import MonitorHolderName
from app.schemas.typings.platform.constrained_strings import ReleaseVersion

MICROSECONDS_PER_SECOND: int = 1_000_000
# The leader looks every interval; it keeps the lead through one missed
# look (a slow database, a long pause), not two.
LEASE_INTERVALS: float = 2.5


def may_lead(
    mark: PlatformMonitorDocument | None,
    holder: MonitorHolderName,
    now: Microseconds,
) -> bool:
    """No one leads, this process leads, or the leader's lease ran out."""

    if mark is None or mark.holder is None or mark.holder == holder:
        return True

    return mark.lease_until is None or int(mark.lease_until) <= int(now)


def renewed_lease(
    mark: PlatformMonitorDocument | None,
    holder: MonitorHolderName,
    interval: PipelineWatchdogSeconds,
    release: ReleaseVersion | None,
    now: Microseconds,
) -> PlatformMonitorDocument:
    """The watchdog's mark after this process looked: checked now, leading on."""

    lease: int = int(int(interval) * LEASE_INTERVALS * MICROSECONDS_PER_SECOND)
    return PlatformMonitorDocument(
        monitor=PlatformMonitor.PIPELINE_WATCHDOG,
        checked_at=now,
        holder=holder,
        lease_until=Microseconds(int(now) + lease),
        release=release,
        created_at=now if mark is None else mark.created_at,
        updated_at=now,
    )
