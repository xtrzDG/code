import logging
from collections.abc import Mapping
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import QueuedJobOperator, QueuedJobRepoContract
from app.contracts.storage import StorageScopeContract
from app.gateways.worker.held_leases import HeldLeases, new_lease_token
from app.gateways.worker.job_failure_reporter import JobFailureReporter, describe_error
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import ExpiredLeaseRelease, JobClaimRequest
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.platform.constrained_integers import (
    ElapsedMilliseconds,
    JobAttemptCount,
    JobClaimLimit,
    JobLeaseSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobLeaseToken, JobName
from app.schemas.typings.platform.strings import JobErrorText
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.log_formatting import log_fields

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_MILLISECOND: int = 1_000
MAX_QUEUED_JOB_ATTEMPTS: JobAttemptCount = JobAttemptCount(5)
RETRY_BASE_DELAY_SECONDS: int = 30
LEASE_EXPIRED_ERROR: JobErrorText = JobErrorText(
    "Lease expired: the worker stopped or lost the database while running the job."
)


@dataclass(frozen=True)
class QueuedJobOutcome:
    """What running one claimed job did: it ran its handler, it failed."""

    has_run: bool
    has_failed: bool


class QueuedJobRunner:
    """
    Claims due jobs of a lane under a lease, runs each with its handler and
    settles it: DONE, PENDING again with exponential backoff (30 s × 2^n),
    or DEAD after the last attempt or without a handler. A job of one
    business runs in that business's storage scope. A worker that lost the
    lease of a job (it ran past the lease without heartbeats) leaves the
    job's state to its new holder.
    """

    def __init__(
        self,
        queued_job_operators: Mapping[JobName, QueuedJobOperator],
        job_repo: QueuedJobRepoContract,
        wall_clock: WallClock[Microseconds],
        storage_scope: StorageScopeContract,
        held_leases: HeldLeases,
        failure_reporter: JobFailureReporter,
        lease_seconds: JobLeaseSeconds,
    ) -> None:
        self._queued_job_operators: dict[JobName, QueuedJobOperator] = dict(
            queued_job_operators
        )
        self._job_repo: QueuedJobRepoContract = job_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._storage_scope: StorageScopeContract = storage_scope
        self._held_leases: HeldLeases = held_leases
        self._failure_reporter: JobFailureReporter = failure_reporter
        self._lease_seconds: JobLeaseSeconds = lease_seconds

    def claim(
        self,
        lane: JobLane,
        limit: JobClaimLimit,
    ) -> tuple[list[QueuedJobDocument], JobLeaseToken]:
        """Due jobs of the lane, now leased to this worker under one token."""

        now: Microseconds = self._wall_clock.now_unix()
        lease_token: JobLeaseToken = new_lease_token()
        jobs: list[QueuedJobDocument] = self._job_repo.claim_due(
            JobClaimRequest(
                lane=lane,
                now=now,
                limit=limit,
                lease_until=self._lease_end(now),
                lease_token=lease_token,
            )
        )
        for job in jobs:
            self._held_leases.hold_job(job.id, lease_token)
            log_pickup(job, now)

        return jobs, lease_token

    def run(
        self, job: QueuedJobDocument, lease_token: JobLeaseToken
    ) -> QueuedJobOutcome:
        """
        Run one claimed job and settle it; never raises for a job failure.
        Its log lines and error reports name the job and its business.
        """

        with bound_log_context(
            job_name=job.name, job_id=job.id, business_id=job.business_id
        ):
            try:
                return self._run_and_settle(job, lease_token)
            except Exception as error:  # noqa: BLE001 - one job never stops others
                self._failure_reporter.report(job.name, error)
                return QueuedJobOutcome(has_run=False, has_failed=True)
            finally:
                self._held_leases.release_job(job.id)

    def release_expired_leases(self) -> int:
        """The reaper: jobs whose worker died run again (or die); their count."""

        released: list[QueuedJobDocument] = self._job_repo.release_expired_leases(
            ExpiredLeaseRelease(
                now=self._wall_clock.now_unix(),
                max_attempts=MAX_QUEUED_JOB_ATTEMPTS,
                error_text=LEASE_EXPIRED_ERROR,
            )
        )
        for job in released:
            LOGGER.warning(
                "Job %s (%s) lost its worker after attempt %d; now %s",
                job.id,
                job.name,
                int(job.attempts),
                job.status.value,
            )

        return len(released)

    def _run_and_settle(
        self,
        job: QueuedJobDocument,
        lease_token: JobLeaseToken,
    ) -> QueuedJobOutcome:
        operator: QueuedJobOperator | None = self._queued_job_operators.get(job.name)
        if operator is None:
            job.status = QueuedJobStatus.DEAD
            job.last_error = JobErrorText(f"No handler for job {job.name}.")
            self._settle(job, lease_token)
            return QueuedJobOutcome(has_run=False, has_failed=True)

        job_input = QueuedJobInput(
            job_id=job.id,
            job_name=job.name,
            payload=job.payload,
            business_id=job.business_id,
            is_final_attempt=job.attempts >= MAX_QUEUED_JOB_ATTEMPTS,
        )
        try:
            if job.business_id is None:
                operator.operate(job_input)
            else:
                # A job for one business sees only its rows (RLS on Postgres).
                with self._storage_scope.scoped_to_business(job.business_id):
                    operator.operate(job_input)
        except Exception as error:  # noqa: BLE001 - retried with backoff
            self._schedule_retry(job, error)
            self._settle(job, lease_token)
            return QueuedJobOutcome(has_run=True, has_failed=True)

        job.status = QueuedJobStatus.DONE
        job.last_error = None
        self._settle(job, lease_token)
        return QueuedJobOutcome(has_run=True, has_failed=False)

    def _schedule_retry(self, job: QueuedJobDocument, error: Exception) -> None:
        job.last_error = describe_error(error)
        if job.attempts >= MAX_QUEUED_JOB_ATTEMPTS:
            job.status = QueuedJobStatus.DEAD
            self._failure_reporter.report(job.name, error)
            return

        now: int = int(self._wall_clock.now_unix())
        delay_seconds: int = RETRY_BASE_DELAY_SECONDS * 2 ** (int(job.attempts) - 1)
        job.status = QueuedJobStatus.PENDING
        job.run_at = Microseconds(now + delay_seconds * MICROSECONDS_PER_SECOND)

    def _settle(self, job: QueuedJobDocument, lease_token: JobLeaseToken) -> None:
        # Released first: a heartbeat between the settle and the release
        # would find the job no longer running and report a lost lease.
        self._held_leases.release_job(job.id)
        job.lease_until = None
        job.lease_token = None
        job.updated_at = self._wall_clock.now_unix()
        if not self._job_repo.settle(job, lease_token):
            LOGGER.warning(
                "Job %s (%s) finished after its lease was lost; its new "
                "holder decides its state",
                job.id,
                job.name,
            )

    def _lease_end(self, now: Microseconds) -> Microseconds:
        return Microseconds(
            int(now) + int(self._lease_seconds) * MICROSECONDS_PER_SECOND
        )


def log_pickup(job: QueuedJobDocument, claimed_at: Microseconds) -> None:
    """
    One line per claimed job with `pickup_delay_ms`: how long it waited
    between being due (queued for now, or its retry time) and a worker
    taking it, the queue-to-claim SLI of docs/operations/capacity.md.
    """

    delay = ElapsedMilliseconds(
        max(0, (int(claimed_at) - int(job.run_at)) // MICROSECONDS_PER_MILLISECOND)
    )
    with bound_log_context(
        job_name=job.name, job_id=job.id, business_id=job.business_id
    ):
        LOGGER.info(
            "Picked up job %s on the %s lane %d ms after it was due",
            job.name,
            job.lane.value,
            int(delay),
            extra=log_fields(
                pickup_delay_ms=int(delay),
                lane=job.lane.value,
                attempt=int(job.attempts),
            ),
        )
