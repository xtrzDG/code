from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobLane, PeriodicJobRunStatus, QueuedJobStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    ProcessedItemCount,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
    JobSerialKey,
)
from app.schemas.typings.platform.prefixed_id import PeriodicJobRunId, QueuedJobId
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
    """

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
