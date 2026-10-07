from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import (
    JobDeathReason,
    JobLane,
    PeriodicJobRunStatus,
    QueuedJobStatus,
)
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.observability.constrained_strings import TraceParent
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    LostJobLeaseCount,
    ProcessedItemCount,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
    JobSerialKey,
    ReleaseVersion,
    RequestId,
    WorkerHostName,
)
from app.schemas.typings.platform.prefixed_id import (
    PeriodicJobRunId,
    QueuedJobId,
    WorkerInstanceId,
)
from app.schemas.typings.platform.strings import JobErrorText, JobPayloadJson


class QueuedJobDocument(BaseDocument):
    """
    One unit of background work (concept: queue in Postgres for reminders,
    assembly, autotests and retries). Retried with exponential backoff until
    it succeeds or runs out of attempts.

    A worker claims a due job for its `lane` with a lease: the job turns
    RUNNING with `lease_until` and the claim's `lease_token`, the worker
    extends the lease while it runs, and only the holder of the token may
    settle it. A job whose lease expired (its worker died) is released for
    another attempt. Jobs with the same `serial_key` run one at a time.

    Version 2: `lost_leases` counts the attempts in a row that ended
    without a recorded result (the reaper found the lease run out); the
    second one in a row makes the job DEAD instead of a third attempt, and
    `dead_reason` says why a job is DEAD. Both optional; a recorded result
    (done, retry or dead) sets `lost_leases` back to 0.

    Version 3: `request_id` and `trace_parent` of the code that queued the
    job (an API request, a job, a periodic run), both optional: the job's
    log lines carry that request id and its spans continue that trace
    (webhook -> job -> model -> send).
    """

    schema_version: SchemaVersion = SchemaVersion("3")

    id: QueuedJobId = Field(default_factory=QueuedJobId)
    name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None = None
    lane: JobLane = JobLane.DEFAULT
    serial_key: JobSerialKey | None = None
    run_at: Microseconds
    attempts: JobAttemptCount = JobAttemptCount(0)
    status: QueuedJobStatus = QueuedJobStatus.PENDING
    lease_until: Microseconds | None = None
    lease_token: JobLeaseToken | None = None
    last_error: JobErrorText | None = None
    lost_leases: LostJobLeaseCount = LostJobLeaseCount(0)
    dead_reason: JobDeathReason | None = None
    request_id: RequestId | None = None
    trace_parent: TraceParent | None = None


class PeriodicJobRunDocument(BaseDocument):
    """
    The run of one periodic job in one period (a day, an ISO week, or one
    interval), shared by every worker: a job runs only when its period has
    no run yet, so a restart or a second worker never repeats today's
    digest or reminders. A FAILED run may be tried again from `retry_at`;
    a RUNNING run whose lease expired (its worker died) may be taken over.
    """

    id: PeriodicJobRunId = Field(default_factory=PeriodicJobRunId)
    job_name: JobName
    period_key: JobPeriodKey
    status: PeriodicJobRunStatus = PeriodicJobRunStatus.RUNNING
    attempts: JobAttemptCount = JobAttemptCount(1)
    started_at: Microseconds
    lease_until: Microseconds | None = None
    lease_token: JobLeaseToken | None = None
    finished_at: Microseconds | None = None
    retry_at: Microseconds | None = None
    processed_count: ProcessedItemCount | None = None
    last_error: JobErrorText | None = None


class PeriodicJobResult(PersistentDocument):
    """How the last run of one periodic job in a worker process ended."""

    job_name: JobName
    outcome: PeriodicJobOutcome
    finished_at: Microseconds
    processed_count: ProcessedItemCount | None = None


class WorkerHeartbeatDocument(BaseDocument):
    """
    The pulse of one background worker process, written on every tick of
    its periodic thread: which build it runs, since when, and how its
    periodic jobs ended last. GET /readyz reports the age of the freshest
    one (a missing or old pulse means jobs wait); a worker deletes pulses
    older than a day when it starts.
    """

    id: WorkerInstanceId = Field(default_factory=WorkerInstanceId)
    host_name: WorkerHostName
    release: ReleaseVersion | None = None
    started_at: Microseconds
    beat_at: Microseconds
    periodic_results: list[PeriodicJobResult] = Field(
        default_factory=list[PeriodicJobResult]
    )
