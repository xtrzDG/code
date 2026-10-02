"""A controlled clock, scripted job operators and a worker built over them."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.repositories.job_repositories import QueuedJobRepository
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    ProcessedItemCount,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.storage.storage_scope_context import StorageScopeContext

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
        storage_scope=StorageScopeContext(),
    )
    queue = JobQueueFacilitator(job_repo=job_repo, wall_clock=clock.wall_clock())
    return worker, job_repo, queue, reporter
