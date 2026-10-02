"""The background worker keeps going when its queue, a tick or a daily job fails."""

import threading

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.gateways.worker.background_worker import (
    BackgroundWorker,
    PeriodicJobSpec,
    WorkerTickReport,
)
from app.repositories.job_repositories import QueuedJobRepository
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    JobIntervalSeconds,
    ProcessedItemCount,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.worker_fakes import (
    ControlledClock,
    CountingPeriodicOperator,
    RecordingErrorReporter,
    build_worker,
)


class UnreachableQueueRepository(QueuedJobRepository):
    """The job queue fails on the first reads, as during a Postgres restart."""

    def __init__(self, failing_reads: int, error: Exception) -> None:
        super().__init__(
            InMemoryDocumentCollectionAdapter[QueuedJobDocument](QueuedJobDocument)
        )
        self.reads: int = 0
        self._failing_reads: int = failing_reads
        self._error: Exception = error

    def list_due(self, now: Microseconds) -> list[QueuedJobDocument]:
        self.reads += 1
        if self.reads <= self._failing_reads:
            raise self._error

        return super().list_due(now)


class CountingStopEvent(threading.Event):
    """Stops after a number of pauses and never really sleeps."""

    def __init__(self, ticks: int) -> None:
        super().__init__()
        self.pauses: list[float | None] = []
        self._ticks: int = ticks

    def wait(self, timeout: float | None = None) -> bool:
        self.pauses.append(timeout)
        if len(self.pauses) >= self._ticks:
            self.set()

        return self.is_set()


def test_an_unreachable_queue_does_not_stop_the_worker() -> None:
    clock = ControlledClock()
    reporter = RecordingErrorReporter()
    job_repo = UnreachableQueueRepository(1, RuntimeError("connection refused"))
    hourly = CountingPeriodicOperator()
    worker = BackgroundWorker(
        periodic_jobs=[
            PeriodicJobSpec(
                name=JobName("end_trials"),
                interval_seconds=JobIntervalSeconds(3600),
                operator=hourly,
            )
        ],
        queued_job_operators={},
        job_repo=job_repo,
        wall_clock=clock.wall_clock(),
        error_reporter=reporter,
        poll_seconds=WorkerPollSeconds(5),
        storage_scope=StorageScopeContext(),
    )
    stop_event = CountingStopEvent(ticks=3)

    worker.run_forever(stop_event)

    assert job_repo.reads == 3  # every tick read the queue again
    assert len(hourly.ticks) == 1
    assert [str(error) for error in reporter.errors] == ["connection refused"]


class ExplodingWorker(BackgroundWorker):
    """A tick that fails as a whole, as when the error reporter itself fails."""

    def __init__(self, worker: BackgroundWorker, failing_ticks: int) -> None:
        self.__dict__.update(worker.__dict__)
        self.ticks: int = 0
        self._failing_ticks: int = failing_ticks

    def run_once(self) -> WorkerTickReport:
        self.ticks += 1
        if self.ticks <= self._failing_ticks:
            raise ExternalServiceError("database is down")

        return super().run_once()


def test_failed_ticks_back_off_and_the_worker_keeps_ticking() -> None:
    clock = ControlledClock()
    worker, _, _, reporter = build_worker(clock, [], None)
    exploding = ExplodingWorker(worker, failing_ticks=3)
    stop_event = CountingStopEvent(ticks=5)

    exploding.run_forever(stop_event)

    assert exploding.ticks == 5
    assert stop_event.pauses == [10, 20, 40, 5, 5]
    assert reporter.errors == []  # application errors are logged, not reported


def test_a_failed_daily_job_is_retried_within_minutes() -> None:
    clock = ControlledClock()
    flaky = FlakyPeriodicOperator(failures_before_success=1)
    worker, _, _, reporter = build_worker(
        clock,
        [
            PeriodicJobSpec(
                name=JobName("purge_expired_recordings"),
                interval_seconds=JobIntervalSeconds(86_400),
                operator=flaky,
            )
        ],
        None,
    )

    failed = worker.run_once()
    clock.advance(60)
    too_soon = worker.run_once()
    clock.advance(5 * 60)
    retried = worker.run_once()
    clock.advance(60 * 60)
    next_hour = worker.run_once()

    assert (failed.periodic_runs, failed.failures) == (1, 1)
    assert too_soon.periodic_runs == 0
    assert (retried.periodic_runs, retried.failures) == (1, 0)
    assert next_hour.periodic_runs == 0  # the next run is a day after success
    assert len(reporter.errors) == 1


class FlakyPeriodicOperator:
    def __init__(self, failures_before_success: int) -> None:
        self.ticks: list[JobTick] = []
        self._failures_left: int = failures_before_success

    def operate(self, input_data: JobTick) -> JobReport:
        self.ticks.append(input_data)
        if self._failures_left > 0:
            self._failures_left -= 1
            raise RuntimeError("storage blip")

        return JobReport(processed_count=ProcessedItemCount(1))
