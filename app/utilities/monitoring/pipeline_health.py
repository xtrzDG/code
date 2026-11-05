"""
Whether customers' messages flow through the workers, from two readings
any process can take: the freshest worker pulse, and the oldest customer
message waiting for a worker (the inbound lane's due jobs).

- A pulse older than PIPELINE_PULSE_LIMIT_SECONDS (or none) means no
  worker runs its periodic thread: every lane stands still.
- A due customer message older than PIPELINE_WAIT_LIMIT_SECONDS means
  the workers that answer customers are gone or stuck, even when another
  worker (the batch worker) still pulses.

GET /healthz/pipeline answers 503 on either, and the API's pipeline
watchdog alerts on them (docs/operations/runbooks/worker-down.md).
"""

from typed_time_provider import Microseconds

from app.schemas.constants.observability import HealthCheckStatus, PipelineState
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.dto.pipeline_health import (
    PipelineChecks,
    PipelineHealthReport,
    PipelineInboundCheck,
    PipelineWorkerCheck,
)
from app.schemas.typings.monitoring.constrained_integers import (
    LaneJobCount,
    WaitSeconds,
    WorkerPulseAgeSeconds,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
# The readiness check's limit too: a worker beats on every tick of its
# periodic thread (15 s by default), one long periodic job delays a few.
PIPELINE_PULSE_LIMIT_SECONDS: int = 5 * 60
# The INBOUND_BACKLOG alert's threshold (ops/alerts/inbound_backlog.yaml):
# a customer message is picked up within a second while workers run.
PIPELINE_WAIT_LIMIT_SECONDS: int = 120


def seconds_since(moment: Microseconds, now: Microseconds) -> int:
    """Whole seconds from `moment` to `now` (never negative)."""

    return max(0, (int(now) - int(moment)) // MICROSECONDS_PER_SECOND)


def assess_pipeline(
    freshest_pulse: WorkerHeartbeatDocument | None,
    oldest_due: QueuedJobDocument | None,
    waiting: int,
    now: Microseconds,
) -> PipelineHealthReport:
    """FLOWING while a worker pulsed lately and no customer waits too long."""

    pulse_age: int | None = (
        None if freshest_pulse is None else seconds_since(freshest_pulse.beat_at, now)
    )
    oldest_wait: int | None = (
        None if oldest_due is None else seconds_since(oldest_due.run_at, now)
    )
    worker = PipelineWorkerCheck(
        status=(
            HealthCheckStatus.OK
            if pulse_age is not None and pulse_age <= PIPELINE_PULSE_LIMIT_SECONDS
            else HealthCheckStatus.FAILED
        ),
        pulse_age_seconds=(
            None if pulse_age is None else WorkerPulseAgeSeconds(pulse_age)
        ),
        limit_seconds=WorkerPulseAgeSeconds(PIPELINE_PULSE_LIMIT_SECONDS),
    )
    inbound = PipelineInboundCheck(
        status=(
            HealthCheckStatus.FAILED
            if oldest_wait is not None and oldest_wait > PIPELINE_WAIT_LIMIT_SECONDS
            else HealthCheckStatus.OK
        ),
        waiting=LaneJobCount(max(0, waiting)),
        oldest_wait_seconds=None if oldest_wait is None else WaitSeconds(oldest_wait),
        limit_seconds=WaitSeconds(PIPELINE_WAIT_LIMIT_SECONDS),
    )
    return PipelineHealthReport(
        status=(
            PipelineState.FLOWING
            if worker.status is HealthCheckStatus.OK
            and inbound.status is HealthCheckStatus.OK
            else PipelineState.STALLED
        ),
        checks=PipelineChecks(worker=worker, inbound=inbound),
    )


def unreadable_pipeline() -> PipelineHealthReport:
    """The database could not tell: nothing vouches for the workers."""

    return PipelineHealthReport(
        status=PipelineState.STALLED,
        checks=PipelineChecks(
            worker=PipelineWorkerCheck(
                status=HealthCheckStatus.FAILED,
                limit_seconds=WorkerPulseAgeSeconds(PIPELINE_PULSE_LIMIT_SECONDS),
            ),
            inbound=PipelineInboundCheck(
                status=HealthCheckStatus.FAILED,
                limit_seconds=WaitSeconds(PIPELINE_WAIT_LIMIT_SECONDS),
            ),
        ),
    )
