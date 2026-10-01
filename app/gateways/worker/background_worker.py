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
    them as attempted before running. Failures of one job never stop others;
    unexpected errors go to the error reporter.
    """

    def __init__(
        self,
        periodic_jobs: Sequence[PeriodicJobSpec],
        queued_job_operators: Mapping[JobName, QueuedJobOperator],
        job_repo: QueuedJobRepoContract,
        wall_clock: WallClock[Microseconds],
        error_reporter: ErrorReportingFacilitatorContract,
        poll_seconds: WorkerPollSeconds,
    ) -> None:
        self._periodic_jobs: list[PeriodicJobSpec] = list(periodic_jobs)
        self._queued_job_operators: dict[JobName, QueuedJobOperator] = dict(
            queued_job_operators
        )
        self._job_repo: QueuedJobRepoContract = job_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._error_reporter: ErrorReportingFacilitatorContract = error_reporter
        self._poll_seconds: WorkerPollSeconds = poll_seconds
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
        """Tick until `stop_event` is set."""

        while not stop_event.is_set():
            self.run_once()
            stop_event.wait(timeout=int(self._poll_seconds))

    def _run_due_periodic_jobs(self) -> tuple[int, int]:
        runs: int = 0
        failures: int = 0
        for job in self._periodic_jobs:
            now: int = int(self._wall_clock.now_unix())
            last_run: int | None = self._last_periodic_runs.get(job.name)
            interval: int = int(job.interval_seconds) * MICROSECONDS_PER_SECOND
            if last_run is not None and now - last_run < interval:
                continue

            self._last_periodic_runs[job.name] = now
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
            except Exception as error:  # noqa: BLE001 - isolate job failures
                failures += 1
                self._report(job.name, error)

        return runs, failures

    def _run_due_queued_jobs(self) -> tuple[int, int]:
        runs: int = 0
        failures: int = 0
        now: Microseconds = self._wall_clock.now_unix()
        for job in self._job_repo.list_due(now):
            operator: QueuedJobOperator | None = self._queued_job_operators.get(
                job.name
            )
            attempts: int = int(job.attempts) + 1
            job.attempts = JobAttemptCount(attempts)
            job.updated_at = now
            if operator is None:
                job.status = QueuedJobStatus.DEAD
                job.last_error = JobErrorText(f"No handler for job {job.name}.")
                self._job_repo.save(job)
                failures += 1
                continue

            self._job_repo.save(job)
            runs += 1
            try:
                operator.operate(
                    QueuedJobInput(
                        job_id=job.id,
                        job_name=job.name,
                        payload=job.payload,
                        business_id=job.business_id,
                        is_final_attempt=attempts >= MAX_QUEUED_JOB_ATTEMPTS,
                    )
                )
            except Exception as error:  # noqa: BLE001 - retried with backoff
                failures += 1
                self._schedule_retry(job, now, error)
                continue

            job.status = QueuedJobStatus.DONE
            job.last_error = None
            self._job_repo.save(job)

        return runs, failures

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
