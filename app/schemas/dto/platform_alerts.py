"""
The platform alerts: the rules (ops/alerts/*.yaml), what one check of a
rule measured, the shared signal counters behind the rate rules, and the
message one alert sends to one recipient (a queued job's payload).
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.incidents import IncidentSeverity
from app.schemas.constants.monitoring import (
    AlertUnit,
    PlatformAlertCode,
    PlatformSignal,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.monitoring.booleans import IsAlertFiring
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
    AlertVolumeFloor,
    AlertWindowMinutes,
    SignalEventCount,
)
from app.schemas.typings.monitoring.constrained_strings import AlertRunbookPath
from app.schemas.typings.monitoring.strings import (
    AlertDetailText,
    AlertRuleSummary,
    PlatformAlertMessage,
)


class PlatformAlertRule(ImmutableDTO):
    """
    One platform alert as ops/alerts/*.yaml defines it: it fires when its
    figure, measured over the window, reaches the threshold (a rate rule
    only once the window holds `volume_floor` events), and points to the
    runbook of what to do. A burn-rate rule also names its short window
    (`short_window_minutes`): it fires only when both windows burn.
    """

    code: PlatformAlertCode
    severity: IncidentSeverity
    summary: AlertRuleSummary
    threshold: AlertThreshold
    unit: AlertUnit
    window_minutes: AlertWindowMinutes
    volume_floor: AlertVolumeFloor = AlertVolumeFloor(0)
    runbook: AlertRunbookPath
    short_window_minutes: AlertWindowMinutes | None = None


class AlertObservation(ImmutableDTO):
    """
    What one check of one rule measured, the threshold it was compared
    with (the rule's own, or for a spike the multiple of the usual level),
    and whether the rule fires.
    """

    code: PlatformAlertCode
    figure: AlertFigure
    threshold: AlertThreshold
    unit: AlertUnit
    detail: AlertDetailText
    is_firing: IsAlertFiring


class SignalTally(ImmutableDTO):
    """
    The events of one signal in the shared window that holds the moment of
    the read (still filling) and in the complete window before it.
    """

    signal: PlatformSignal
    current: SignalEventCount
    previous: SignalEventCount


class PlatformAlertDelivery(ImmutableDTO):
    """
    The payload of one `send_platform_alert` job: one alert's message to
    one recipient of the team (a Telegram chat of the platform bot or an
    e-mail address). The job queue retries it with backoff.
    """

    channel: ManagerContactChannel
    address: ManagerContactAddress
    text: PlatformAlertMessage
