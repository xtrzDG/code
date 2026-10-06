"""
The alerts about the pipeline itself, as the API's watchdog and the
workers' `platform_alerts` job both observe them: WORKER_DOWN (no worker
pulsed within five minutes) and INBOUND_BACKLOG (a customer message
waited more than two), from one reading of the pipeline
(app/utilities/monitoring/pipeline_health.py).
"""

from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.health import WorkerHeartbeatRepoContract
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.dto.pipeline_health import PipelineHealthReport
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.typings.monitoring.constrained_integers import AlertFigure
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.use_cases.admin.alerts.alert_texts import describe_duration
from app.utilities.monitoring.pipeline_health import seconds_since

PIPELINE_ALERT_CODES: tuple[PlatformAlertCode, ...] = (
    PlatformAlertCode.WORKER_DOWN,
    PlatformAlertCode.INBOUND_BACKLOG,
)


def worker_down_observation(
    rule: PlatformAlertRule, pulse_age_seconds: int | None
) -> AlertObservation:
    """Fires when the freshest pulse is older than the rule allows, or missing."""

    if pulse_age_seconds is None:
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(0),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(
                "No worker pulse is stored: no worker ran in the last day."
            ),
            is_firing=True,
        )

    return AlertObservation(
        code=rule.code,
        figure=AlertFigure(pulse_age_seconds),
        threshold=rule.threshold,
        unit=rule.unit,
        detail=AlertDetailText(
            f"The freshest worker pulse is {describe_duration(pulse_age_seconds)} old."
        ),
        is_firing=pulse_age_seconds > int(rule.threshold),
    )


def backlog_observation(
    rule: PlatformAlertRule, oldest_wait_seconds: int | None, waiting: int
) -> AlertObservation:
    """Fires when the oldest due customer message waited longer than the rule allows."""

    waited: int = oldest_wait_seconds or 0
    return AlertObservation(
        code=rule.code,
        figure=AlertFigure(waited),
        threshold=rule.threshold,
        unit=rule.unit,
        detail=AlertDetailText(
            f"The oldest of {waiting} waiting customer messages has waited "
            f"{describe_duration(waited)}."
            if oldest_wait_seconds is not None
            else "No customer message waits for a worker."
        ),
        is_firing=waited > int(rule.threshold),
    )


def pipeline_observations(
    report: PipelineHealthReport,
    rules: Mapping[PlatformAlertCode, PlatformAlertRule],
) -> list[AlertObservation]:
    """WORKER_DOWN and INBOUND_BACKLOG from one reading of the pipeline."""

    worker = report.checks.worker
    inbound = report.checks.inbound
    return [
        worker_down_observation(
            rules[PlatformAlertCode.WORKER_DOWN],
            None if worker.pulse_age_seconds is None else int(worker.pulse_age_seconds),
        ),
        backlog_observation(
            rules[PlatformAlertCode.INBOUND_BACKLOG],
            (
                None
                if inbound.oldest_wait_seconds is None
                else int(inbound.oldest_wait_seconds)
            ),
            int(inbound.waiting),
        ),
    ]


class WorkerDownAlertCheck:
    """
    The workers' own look at WORKER_DOWN (for `PlatformAlertChecks`): the
    `platform_alerts` job runs in a live worker, so here it never fires
    (a worker's first tick runs its jobs before its first pulse); it ends
    an episode the API's watchdog started, once a worker is back.
    """

    def __init__(self, heartbeat_repo: WorkerHeartbeatRepoContract) -> None:
        self._heartbeats: WorkerHeartbeatRepoContract = heartbeat_repo

    def check(self, rule: PlatformAlertRule, now: Microseconds) -> AlertObservation:
        freshest = self._heartbeats.find_freshest()
        age: int = 0 if freshest is None else seconds_since(freshest.beat_at, now)
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(age),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(
                "A worker runs the platform alerts: the workers are back."
            ),
            is_firing=False,
        )
