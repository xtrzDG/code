"""Time-triggered transport: runs periodic jobs and drains the job queue."""

import logging
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import (
    PeriodicJobOperator,
    QueuedJobOperator,
    QueuedJobRepoContract,
)
from app.contracts.observability import ErrorReportingFacilitatorContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobIntervalSeconds,
    ProcessedItemCount,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobErrorText

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_QUEUED_JOB_ATTEMPTS: int = 5
RETRY_BASE_DELAY_SECONDS: int = 30
MAX_ERROR_TEXT_LENGTH: int = 500
# A failed periodic job is retried after this long (or its own interval,
# when shorter) instead of waiting a whole interval, up to a day.
PERIODIC_RETRY_SECONDS: int = 5 * 60
# After a tick that failed as a whole (the database is down), wait longer
# and longer between ticks, up to this many seconds.
MAX_TICK_BACKOFF_SECONDS: int = 5 * 60


@dataclass(frozen=True)
class PeriodicJobSpec:
    """A periodic job: name, interval and the operator that runs it."""

    name: JobName
    interval_seconds: JobIntervalSeconds
    operator: PeriodicJobOperator


class WorkerTickReport(ImmutableDTO):
    """What one scheduler tick did."""

    periodic_runs: ProcessedItemCount
    queued_runs: ProcessedItemCount
    failures: ProcessedItemCount


class BackgroundWorker:
    """
    Runs periodic jobs (reminders, retention purge, grace periods, journal
    flush) and queued jobs (autotests, retries) with exponential backoff.

    One worker process is assumed: due queued jobs are claimed by marking
    them as attempted before running. A queued job of one business runs in
    that business's storage scope. Failures of one job never stop others,
    and a storage outage never stops the worker: the tick is reported and
    the next one comes after a growing pause. A failed periodic job is
    retried within minutes, not after its whole interval. Unexpected errors
    go to the error reporter.
    """

    def __init__(
        self,
        periodic_jobs: Sequence[PeriodicJobSpec],
        queued_job_operators: Mapping[JobName, QueuedJobOperator],
        job_repo: QueuedJobRepoContract,
        wall_clock: WallClock[Microseconds],
        error_reporter: ErrorReportingFacilitatorContract,
        poll_seconds: WorkerPollSeconds,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._periodic_jobs: list[PeriodicJobSpec] = list(periodic_jobs)
        self._queued_job_operators: dict[JobName, QueuedJobOperator] = dict(
            queued_job_operators
        )
        self._job_repo: QueuedJobRepoContract = job_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._error_reporter: ErrorReportingFacilitatorContract = error_reporter
        self._poll_seconds: WorkerPollSeconds = poll_seconds
        self._storage_scope: StorageScopeContract = storage_scope
        self._last_periodic_runs: dict[JobName, int] = {}

    def run_once(self) -> WorkerTickReport:
        """Run every due periodic job and every due queued job once."""

        periodic_runs, periodic_failures = self._run_due_periodic_jobs()
        queued_runs, queued_failures = self._run_due_queued_jobs()
        return WorkerTickReport(
            periodic_runs=ProcessedItemCount(periodic_runs),
            queued_runs=ProcessedItemCount(queued_runs),
            failures=ProcessedItemCount(periodic_failures + queued_failures),
        )

    def run_forever(self, stop_event: threading.Event) -> None:
        """
        Tick until `stop_event` is set. A tick that fails as a whole is
        reported and followed by a pause that doubles with every further
        failure (at most MAX_TICK_BACKOFF_SECONDS).
        """

        consecutive_failures: int = 0
        while not stop_event.is_set():
            try:
                self.run_once()
                consecutive_failures = 0
            except Exception as error:  # noqa: BLE001 - the worker must survive
                consecutive_failures += 1
                self._report(JobName("worker_tick"), error)

            stop_event.wait(timeout=self._pause_seconds(consecutive_failures))

    def _pause_seconds(self, consecutive_failures: int) -> int:
        poll_seconds: int = int(self._poll_seconds)
        if consecutive_failures == 0:
            return poll_seconds

        backoff_seconds: int = poll_seconds * (1 << consecutive_failures)
        return min(backoff_seconds, max(poll_seconds, MAX_TICK_BACKOFF_SECONDS))

    def _run_due_periodic_jobs(self) -> tuple[int, int]:
        runs: int = 0
        failures: int = 0
        for job in self._periodic_jobs:
            now: int = int(self._wall_clock.now_unix())
            last_run: int | None = self._last_periodic_runs.get(job.name)
            interval: int = int(job.interval_seconds) * MICROSECONDS_PER_SECOND
            if last_run is not None and now - last_run < interval:
                continue

            runs += 1
            try:
                report: JobReport = job.operator.operate(
                    JobTick(job_name=job.name, scheduled_at=Microseconds(now))
                )
                LOGGER.info(
                    "Periodic job %s processed %d items",
                    job.name,
                    report.processed_count,
                )
                self._last_periodic_runs[job.name] = now
            except Exception as error:  # noqa: BLE001 - isolate job failures
                failures += 1
                # Due again after the retry delay rather than a full interval.
                retry: int = min(
                    interval, PERIODIC_RETRY_SECONDS * MICROSECONDS_PER_SECOND
                )
                self._last_periodic_runs[job.name] = now - interval + retry
                self._report(job.name, error)

        return runs, failures

    def _run_due_queued_jobs(self) -> tuple[int, int]:
        runs: int = 0
        failures: int = 0
        now: Microseconds = self._wall_clock.now_unix()
        try:
            due_jobs: list[QueuedJobDocument] = self._job_repo.list_due(now)
        except Exception as error:  # noqa: BLE001 - the queue may be unreachable
            self._report(JobName("job_queue"), error)
            return runs, failures + 1

        for job in due_jobs:
            try:
                has_run, has_failed = self._run_queued_job(job, now)
            except Exception as error:  # noqa: BLE001 - one job never stops others
                has_run, has_failed = False, True
                self._report(job.name, error)

            runs += int(has_run)
            failures += int(has_failed)

        return runs, failures

    def _run_queued_job(
        self,
        job: QueuedJobDocument,
        now: Microseconds,
    ) -> tuple[bool, bool]:
        """Claim, run and settle one queued job: (was run, failed)."""

        operator: QueuedJobOperator | None = self._queued_job_operators.get(job.name)
        attempts: int = int(job.attempts) + 1
        job.attempts = JobAttemptCount(attempts)
        job.updated_at = now
        if operator is None:
            job.status = QueuedJobStatus.DEAD
            job.last_error = JobErrorText(f"No handler for job {job.name}.")
            self._job_repo.save(job)
            return False, True

        self._job_repo.save(job)
        job_input = QueuedJobInput(
            job_id=job.id,
            job_name=job.name,
            payload=job.payload,
            business_id=job.business_id,
            is_final_attempt=attempts >= MAX_QUEUED_JOB_ATTEMPTS,
        )
        try:
            if job.business_id is None:
                operator.operate(job_input)
            else:
                # A job for one business sees only its rows (RLS on Postgres).
                with self._storage_scope.scoped_to_business(job.business_id):
                    operator.operate(job_input)
        except Exception as error:  # noqa: BLE001 - retried with backoff
            self._schedule_retry(job, now, error)
            return True, True

        job.status = QueuedJobStatus.DONE
        job.last_error = None
        self._job_repo.save(job)
        return True, False

    def _schedule_retry(
        self,
        job: QueuedJobDocument,
        now: Microseconds,
        error: Exception,
    ) -> None:
        job.last_error = JobErrorText(describe_error(error))
        if int(job.attempts) >= MAX_QUEUED_JOB_ATTEMPTS:
            job.status = QueuedJobStatus.DEAD
            self._report(job.name, error)
        else:
            delay_seconds: int = RETRY_BASE_DELAY_SECONDS * 2 ** (int(job.attempts) - 1)
            job.run_at = Microseconds(
                int(now) + delay_seconds * MICROSECONDS_PER_SECOND
            )

        self._job_repo.save(job)

    def _report(self, job_name: JobName, error: Exception) -> None:
        if isinstance(error, ApplicationError):
            LOGGER.warning("Job %s failed: %s", job_name, error)
            return

        self._error_reporter.capture_exception(error)


def describe_error(error: Exception) -> str:
    text: str = f"{type(error).__name__}: {error}"
    return text[:MAX_ERROR_TEXT_LENGTH]
