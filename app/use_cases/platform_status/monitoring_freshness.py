"""
Whether the status page may trust the alert levels: the workers'
`platform_alerts` job marks every run (`platform_monitors`, ALERT_CHECKS).
The alert states change only when an episode starts, repeats or ends, so a
quiet platform and a platform whose checks stopped look the same in them;
the mark tells them apart. When it is older than MONITORING_STALE_MINUTES,
nothing vouches for the chat channels: they count as degraded, and the
page says the monitoring is delayed. Before the first run of a new
platform there is no mark and nothing to be late against: the page shows
the alert levels as they are (and no time of the last check).
"""

from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.schemas.constants.platform_status import StatusComponent, StatusLevel
from app.schemas.domain.platform_monitors import PlatformMonitorDocument
from app.use_cases.platform_status.component_levels import CHAT_CHANNELS, worse

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000
# Three runs of the five-minute job missed: past a deploy or one slow run.
MONITORING_STALE_MINUTES: int = 15


def last_alert_check(mark: PlatformMonitorDocument | None) -> Microseconds | None:
    """When the alert checks last finished (None before the first)."""

    return None if mark is None else mark.checked_at


def is_monitoring_delayed(last_check: Microseconds | None, now: Microseconds) -> bool:
    """The last check is older than the limit (never ran: not late yet)."""

    return (
        last_check is not None
        and int(now) - int(last_check)
        > MONITORING_STALE_MINUTES * MICROSECONDS_PER_MINUTE
    )


def with_monitoring_delay(
    levels: Mapping[StatusComponent, StatusLevel], is_delayed: bool
) -> dict[StatusComponent, StatusLevel]:
    """The levels, with the chat channels at least degraded while delayed."""

    adjusted: dict[StatusComponent, StatusLevel] = dict(levels)
    if not is_delayed:
        return adjusted

    for component in CHAT_CHANNELS:
        adjusted[component] = worse(
            adjusted.get(component, StatusLevel.OPERATIONAL), StatusLevel.DEGRADED
        )
    return adjusted
