from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformMonitor
from app.schemas.typings.monitoring.constrained_strings import MonitorHolderName
from app.schemas.typings.platform.constrained_strings import ReleaseVersion


class PlatformMonitorDocument(BaseDocument):
    """
    The mark of one watcher of the platform (a platform collection stored
    under the watcher's name, 1173): when it last finished a look
    (`checked_at`) and, for the API's pipeline watchdog, which API process
    leads it (`holder`) until when (`lease_until`).

    The status page trusts the alert levels only while the ALERT_CHECKS
    mark is fresh: the alert states themselves are written only when an
    alert starts, repeats or ends, so they cannot tell a quiet platform
    from a dead worker. The watchdog's lease is taken and renewed under
    the alert-state lock; another API process takes it over once it ran
    out (its leader died or stalled).
    """

    monitor: PlatformMonitor
    checked_at: Microseconds
    holder: MonitorHolderName | None = None
    lease_until: Microseconds | None = None
    release: ReleaseVersion | None = None
