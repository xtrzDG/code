"""
Requests of the leased job queue and of periodic job runs (worker side).

A worker claims due jobs of one lane with a lease, extends the lease while
they run, and settles each job only while it still holds the lease. Jobs
whose lease ran out (their worker died) are released for another attempt.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobClaimLimit,
    LostJobLeaseCount,
    PageSize,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobErrorText


class JobClaimRequest(ImmutableDTO):
    """
    Claim up to `limit` due PENDING jobs of `lane`, oldest first, at most one
    per serial key and none whose serial key already runs. Claimed jobs turn
    RUNNING with one more attempt, `lease_until` and `lease_token`.
    """

    lane: JobLane
    now: Microseconds
    limit: JobClaimLimit
    lease_until: Microseconds
    lease_token: JobLeaseToken


class HeldJobLease(ImmutableDTO):
    """A job a worker runs right now, with the token of its claim."""

    job_id: QueuedJobId
    lease_token: JobLeaseToken


class JobLeaseExtension(ImmutableDTO):
    """Heartbeat: move the lease of these held jobs to `lease_until`."""

    leases: list[HeldJobLease]
    lease_until: Microseconds


class ExpiredLeaseRelease(ImmutableDTO):
    """
    Reaper: RUNNING jobs whose lease ended before `now` count one more lost
    lease and go back to PENDING (due at once), with `error_text` as their
    last error. A job whose lost leases in a row reach `max_lost_leases`
    (its attempts keep taking their worker process down) goes to DEAD with
    the reason `process_died` and `process_died_text` instead; one that
    used `max_attempts` to DEAD with the reason `attempts_exhausted`.
    """

    now: Microseconds
    max_attempts: JobAttemptCount
    error_text: JobErrorText
    max_lost_leases: LostJobLeaseCount
    process_died_text: JobErrorText


class QueuedJobPosition(ImmutableDTO):
    """Where a page of queued jobs (newest change first) ended."""

    updated_at: Microseconds
    job_id: QueuedJobId


class QueuedJobPageQuery(ImmutableDTO):
    """
    Queued jobs, the most recently changed first, optionally of one status
    and one job name, after `after` (keyset paging). The store returns up to
    `page_size` + 1 jobs, so the caller knows whether another page follows.
    """

    status: QueuedJobStatus | None = None
    name: JobName | None = None
    after: QueuedJobPosition | None = None
    page_size: PageSize


class PeriodicRunStart(ImmutableDTO):
    """
    A worker asks to run periodic job `job_name` in period `period_key` now,
    under a lease until `lease_until` held with `lease_token`.
    """

    job_name: JobName
    period_key: JobPeriodKey
    now: Microseconds
    lease_until: Microseconds
    lease_token: JobLeaseToken


class PeriodicRunLease(ImmutableDTO):
    """Heartbeat of a running periodic job: its run and the claim's token."""

    job_name: JobName
    period_key: JobPeriodKey
    lease_token: JobLeaseToken
    lease_until: Microseconds
