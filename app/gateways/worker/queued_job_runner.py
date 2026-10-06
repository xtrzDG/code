import logging
from collections.abc import Mapping
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import QueuedJobOperator, QueuedJobRepoContract
from app.contracts.storage import StorageScopeContract
from app.gateways.worker.held_leases import HeldLeases, new_lease_token
from app.gateways.worker.job_failure_reporter import JobFailureReporter, describe_error
from app.gateways.worker.job_run_logs import (
    JobRunStart,
    log_job_finished,
    log_pickup,
    start_job_run,
)
from app.schemas.constants.jobs import JobDeathReason, JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import ExpiredLeaseRelease, JobClaimRequest
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobClaimLimit,
    JobLeaseSeconds,
    LostJobLeaseCount,
)
from app.schemas.typings.platform.constrained_strings import JobLeaseToken, JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobErrorText
from app.utilities.observability.log_context import bound_log_context

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_QUEUED_JOB_ATTEMPTS: JobAttemptCount = JobAttemptCount(5)
# The second attempt in a row that ends with its worker process is the last:
# a job that kills its process is set aside instead of taking down the next
# worker too (and the next).
MAX_LOST_LEASES: LostJobLeaseCount = LostJobLeaseCount(2)
RETRY_BASE_DELAY_SECONDS: int = 30
LEASE_EXPIRED_ERROR: JobErrorText = JobErrorText(
    "Lease expired: the worker stopped or lost the database while running the job."
)
PROCESS_DIED_ERROR: JobErrorText = JobErrorText(
    "process_died: two attempts in a row ended with their worker process "
    "(killed or out of memory) before the job recorded a result; it is not "
    "tried again. Find the cause (rss_before_mb/rss_after_mb in the worker "
    "logs), then retry it from the admin jobs page."
)


class JobKilledItsWorkerError(RuntimeError):
    """A queued job's attempts keep ending with their worker process."""


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
    job's state to its new holder. A job whose worker process died with it
    twice in a row is DEAD (process_died) instead of a third attempt, and
    every job's log line says how much memory the process held before and
    after it.
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
            start: JobRunStart = start_job_run()
            try:
                outcome = self._run_and_settle(job, lease_token)
            except Exception as error:  # noqa: BLE001 - one job never stops others
                self._failure_reporter.report(job.name, error)
                outcome = QueuedJobOutcome(has_run=False, has_failed=True)
            finally:
                self._held_leases.release_job(job.id)
            log_job_finished(job.name, finished_state(job), start)
            return outcome

    def release_expired_leases(self) -> int:
        """The reaper: jobs whose worker died run again (or die); their count."""

        released: list[QueuedJobDocument] = self._job_repo.release_expired_leases(
            ExpiredLeaseRelease(
                now=self._wall_clock.now_unix(),
                max_attempts=MAX_QUEUED_JOB_ATTEMPTS,
                error_text=LEASE_EXPIRED_ERROR,
                max_lost_leases=MAX_LOST_LEASES,
                process_died_text=PROCESS_DIED_ERROR,
            )
        )
        for job in released:
            if job.dead_reason is JobDeathReason.PROCESS_DIED:
                self._report_poison_job(job)
                continue

            LOGGER.warning(
                "Job %s (%s) lost its worker after attempt %d; now %s",
                job.id,
                job.name,
                int(job.attempts),
                job.status.value,
            )

        return len(released)

    def hand_back_running_jobs(self) -> list[QueuedJobId]:
        """
        On a stop whose grace period ran out: every job still running here
        goes back to the queue, due at once for another worker, without
        counting as a failed attempt or a lost lease (a deploy is not a
        crash). A job that finishes after all finds its lease gone.
        """

        now: Microseconds = self._wall_clock.now_unix()
        handed_back: list[QueuedJobId] = []
        for lease in self._held_leases.jobs():
            self._held_leases.release_job(lease.job_id)
            if self._job_repo.hand_back(lease, now):
                handed_back.append(lease.job_id)

        if handed_back:
            LOGGER.warning(
                "Handed %d running jobs back to the queue on stop: %s",
                len(handed_back),
                ", ".join(str(job_id) for job_id in handed_back),
            )

        return handed_back

    def _report_poison_job(self, job: QueuedJobDocument) -> None:
        """An error report (Sentry) and the dead_jobs alert, not a retry."""

        with bound_log_context(
            job_name=job.name, job_id=job.id, business_id=job.business_id
        ):
            self._failure_reporter.report(
                job.name,
                JobKilledItsWorkerError(
                    f"Job {job.id} ({job.name}) ended with its worker process "
                    f"{int(job.lost_leases)} times in a row; it is dead "
                    "(process_died) instead of taking down another worker."
                ),
            )

    def _run_and_settle(
        self,
        job: QueuedJobDocument,
        lease_token: JobLeaseToken,
    ) -> QueuedJobOutcome:
        operator: QueuedJobOperator | None = self._queued_job_operators.get(job.name)
        if operator is None:
            job.status = QueuedJobStatus.DEAD
            job.dead_reason = JobDeathReason.NO_HANDLER
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
        job.dead_reason = None
        self._settle(job, lease_token)
        return QueuedJobOutcome(has_run=True, has_failed=False)

    def _schedule_retry(self, job: QueuedJobDocument, error: Exception) -> None:
        job.last_error = describe_error(error)
        if job.attempts >= MAX_QUEUED_JOB_ATTEMPTS:
            job.status = QueuedJobStatus.DEAD
            job.dead_reason = JobDeathReason.ATTEMPTS_EXHAUSTED
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
        # A recorded result: the attempt did not end with its process.
        job.lost_leases = LostJobLeaseCount(0)
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


def finished_state(job: QueuedJobDocument) -> str:
    """How a run ended for its log line: the settled status, else failed."""

    return "failed" if job.status is QueuedJobStatus.RUNNING else job.status.value
