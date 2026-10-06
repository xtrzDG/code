"""
Whether customers' messages flow through the workers, seen from the API
(GET /healthz/pipeline and the API's pipeline watchdog): the freshest
worker pulse and the oldest customer message waiting for a worker.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.observability import HealthCheckStatus, PipelineState
from app.schemas.typings.monitoring.booleans import IsWatchdogLeader
from app.schemas.typings.monitoring.constrained_integers import (
    LaneJobCount,
    NotificationCount,
    WaitSeconds,
    WorkerPulseAgeSeconds,
)


class PipelineHealthQuery(ImmutableDTO):
    """Ask whether customers' messages flow through the workers."""


class PipelineWorkerCheck(ImmutableDTO):
    """
    The freshest pulse of any background worker: OK while it is at most
    `limit_seconds` old, FAILED when older or missing (no worker runs).
    """

    status: HealthCheckStatus
    pulse_age_seconds: WorkerPulseAgeSeconds | None = None
    limit_seconds: WorkerPulseAgeSeconds


class PipelineInboundCheck(ImmutableDTO):
    """
    The customer messages waiting for a worker (the inbound lane's due
    jobs): OK while the oldest waited at most `limit_seconds`.
    """

    status: HealthCheckStatus
    waiting: LaneJobCount = LaneJobCount(0)
    oldest_wait_seconds: WaitSeconds | None = None
    limit_seconds: WaitSeconds


class PipelineChecks(ImmutableDTO):
    worker: PipelineWorkerCheck
    inbound: PipelineInboundCheck


class PipelineHealthReport(ImmutableDTO):
    """FLOWING while both checks are OK; STALLED otherwise (HTTP 503)."""

    status: PipelineState
    checks: PipelineChecks


class PipelineWatchTick(ImmutableDTO):
    """One look of the API's pipeline watchdog (every PIPELINE_WATCHDOG_SECONDS)."""


class PipelineWatchReport(ImmutableDTO):
    """
    What one look did: whether this API process leads the watchdog (only
    the leader checks), what it found, and how many alert messages it
    sent straight to the team (none while an episode is in its cooldown).
    """

    is_leader: IsWatchdogLeader = False
    pipeline: PipelineState | None = None
    sent_count: NotificationCount = NotificationCount(0)
