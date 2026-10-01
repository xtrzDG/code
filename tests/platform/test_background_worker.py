from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.repositories.job_repositories import QueuedJobRepository
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    JobIntervalSeconds,
    ProcessedItemCount,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson

SECOND_IN_NANOSECONDS: int = 1_000_000_000
START_NANOSECONDS: int = 1_790_000_000 * SECOND_IN_NANOSECONDS


class ControlledClock:
    def __init__(self) -> None:
        self.nanoseconds: int = START_NANOSECONDS

    def advance(self, seconds: int) -> None:
        self.nanoseconds += seconds * SECOND_IN_NANOSECONDS

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.nanoseconds,
        )


class CountingPeriodicOperator:
    def __init__(self, should_fail: bool = False) -> None:
        self.ticks: list[JobTick] = []
        self._should_fail: bool = should_fail

    def operate(self, input_data: JobTick) -> JobReport:
        self.ticks.append(input_data)
        if self._should_fail:
            raise RuntimeError("unexpected")

        return JobReport(processed_count=ProcessedItemCount(1))


class FlakyQueuedOperator:
    def __init__(self, failures_before_success: int) -> None:
        self.calls: list[QueuedJobInput] = []
        self._failures_left: int = failures_before_success

    def operate(self, input_data: QueuedJobInput) -> JobReport:
        self.calls.append(input_data)
        if self._failures_left > 0:
            self._failures_left -= 1
            raise ExternalServiceError("provider down")

        return JobReport(processed_count=ProcessedItemCount(1))


class RecordingErrorReporter:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def capture_exception(self, error: BaseException) -> None:
        self.errors.append(error)


def build_worker(
    clock: ControlledClock,
    periodic_jobs: list[PeriodicJobSpec],
    queued_operator: FlakyQueuedOperator | None,
) -> tuple[
    BackgroundWorker, QueuedJobRepository, JobQueueFacilitator, RecordingErrorReporter
]:
    job_repo = QueuedJobRepository(
        InMemoryDocumentCollectionAdapter[QueuedJobDocument](QueuedJobDocument)
    )
    reporter = RecordingErrorReporter()
    worker = BackgroundWorker(
        periodic_jobs=periodic_jobs,
        queued_job_operators=(
            {}
            if queued_operator is None
            else {JobName("run_autotests"): queued_operator}
        ),
        job_repo=job_repo,
        wall_clock=clock.wall_clock(),
        error_reporter=reporter,
        poll_seconds=WorkerPollSeconds(5),
    )
    queue = JobQueueFacilitator(job_repo=job_repo, wall_clock=clock.wall_clock())
    return worker, job_repo, queue, reporter


def test_periodic_jobs_respect_their_interval_and_isolate_failures() -> None:
    clock = ControlledClock()
    hourly = CountingPeriodicOperator()
    broken = CountingPeriodicOperator(should_fail=True)
    worker, _, _, reporter = build_worker(
        clock,
        [
            PeriodicJobSpec(
                name=JobName("purge_expired_recordings"),
                interval_seconds=JobIntervalSeconds(3600),
                operator=hourly,
            ),
            PeriodicJobSpec(
                name=JobName("broken_job"),
                interval_seconds=JobIntervalSeconds(60),
                operator=broken,
            ),
        ],
        None,
    )

    first = worker.run_once()
    clock.advance(120)
    second = worker.run_once()
    clock.advance(3600)
    worker.run_once()

    assert first.periodic_runs == 2 and first.failures == 1
    assert second.periodic_runs == 1
    assert len(hourly.ticks) == 2
    assert len(broken.ticks) == 3
    assert len(reporter.errors) == 3


def test_queued_job_is_retried_with_backoff_then_done() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=2)
    worker, job_repo, queue, reporter = build_worker(clock, [], operator)
    job_id = queue.enqueue(
        JobName("run_autotests"),
        JobPayloadJson('{"assistant_version_id": "v1"}'),
        business_id=None,
    )

    worker.run_once()
    failed_once = job_repo.get(job_id)
    assert failed_once is not None
    assert failed_once.status is QueuedJobStatus.PENDING
    assert failed_once.attempts == 1
    assert failed_once.last_error == "ExternalServiceError: provider down"

    clock.advance(10)
    worker.run_once()
    assert len(operator.calls) == 1

    clock.advance(30)
    worker.run_once()
    clock.advance(60)
    worker.run_once()

    done = job_repo.get(job_id)
    assert done is not None
    assert done.status is QueuedJobStatus.DONE
    assert len(operator.calls) == 3
    assert reporter.errors == []


def test_queued_job_dies_after_max_attempts_or_without_handler() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=100)
    worker, job_repo, queue, reporter = build_worker(clock, [], operator)
    job_id = queue.enqueue(
        JobName("run_autotests"),
        JobPayloadJson("{}"),
        business_id=None,
    )
    orphan_id = queue.enqueue(
        JobName("unknown_job"),
        JobPayloadJson("{}"),
        business_id=None,
    )

    for _ in range(10):
        worker.run_once()
        clock.advance(10_000)

    dead = job_repo.get(job_id)
    orphan = job_repo.get(orphan_id)
    assert dead is not None and dead.status is QueuedJobStatus.DEAD
    assert dead.attempts == 5
    assert orphan is not None and orphan.status is QueuedJobStatus.DEAD
    assert reporter.errors == []
