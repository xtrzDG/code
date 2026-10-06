"""A controlled clock, scripted job operators and a worker built over them."""

import threading
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.in_memory_periodic_job_run_store_adapter import (
    InMemoryPeriodicJobRunStoreAdapter,
)
from app.adapters.storage.in_memory_queued_job_claim_adapter import (
    InMemoryQueuedJobClaimAdapter,
)
from app.contracts.jobs import (
    PeriodicJobRunRepoContract,
    QueuedJobOperator,
    QueuedJobRepoContract,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.repositories.job_repositories import (
    PeriodicJobRunRepository,
    QueuedJobRepository,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.jobs import PeriodicJobRunDocument, QueuedJobDocument
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    ProcessedItemCount,
    WorkerLaneConcurrency,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal
from app.utilities.storage.storage_scope_context import StorageScopeContext

SECOND_IN_NANOSECONDS: int = 1_000_000_000
# 2026-09-21 14:13:20 UTC.
START_NANOSECONDS: int = 1_790_000_000 * SECOND_IN_NANOSECONDS
RUN_AUTOTESTS: JobName = JobName("run_autotests")
TEST_LANE_CONCURRENCY: dict[JobLane, WorkerLaneConcurrency] = {
    JobLane.INBOUND: WorkerLaneConcurrency(2),
    JobLane.OUTBOUND: WorkerLaneConcurrency(1),
    JobLane.DEFAULT: WorkerLaneConcurrency(1),
    JobLane.AUTOTESTS: WorkerLaneConcurrency(2),
}


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


@dataclass
class JobStores:
    """One in-memory queue and periodic run store, shared by workers."""

    job_repo: QueuedJobRepoContract
    periodic_run_repo: PeriodicJobRunRepoContract
    job_wakeup: JobWakeupSignal


def build_job_stores() -> JobStores:
    jobs = InMemoryDocumentCollectionAdapter[QueuedJobDocument](QueuedJobDocument)
    runs = InMemoryDocumentCollectionAdapter[PeriodicJobRunDocument](
        PeriodicJobRunDocument
    )
    return JobStores(
        job_repo=QueuedJobRepository(jobs, InMemoryQueuedJobClaimAdapter(jobs)),
        periodic_run_repo=PeriodicJobRunRepository(
            InMemoryPeriodicJobRunStoreAdapter(runs)
        ),
        job_wakeup=JobWakeupSignal(),
    )


@dataclass
class WorkerKit:
    worker: BackgroundWorker
    stores: JobStores
    queue: JobQueueFacilitator
    reporter: RecordingErrorReporter

    @property
    def job_repo(self) -> QueuedJobRepoContract:
        return self.stores.job_repo


def build_worker(
    clock: ControlledClock,
    periodic_jobs: list[PeriodicJobSpec],
    queued_operators: dict[JobName, QueuedJobOperator] | None = None,
    stores: JobStores | None = None,
    poll_seconds: int = 5,
    lanes: tuple[JobLane, ...] = tuple(JobLane),
    stop_grace_seconds: float = 25.0,
) -> WorkerKit:
    job_stores: JobStores = build_job_stores() if stores is None else stores
    reporter = RecordingErrorReporter()
    worker = BackgroundWorker(
        periodic_jobs=periodic_jobs,
        queued_job_operators={} if queued_operators is None else queued_operators,
        job_repo=job_stores.job_repo,
        periodic_run_repo=job_stores.periodic_run_repo,
        wall_clock=clock.wall_clock(),
        error_reporter=reporter,
        poll_seconds=WorkerPollSeconds(poll_seconds),
        storage_scope=StorageScopeContext(),
        job_wakeup=job_stores.job_wakeup,
        lane_concurrency=TEST_LANE_CONCURRENCY,
        lanes=lanes,
        stop_grace_seconds=stop_grace_seconds,
    )
    queue = JobQueueFacilitator(
        job_repo=job_stores.job_repo,
        wall_clock=clock.wall_clock(),
        job_wakeup=job_stores.job_wakeup,
    )
    return WorkerKit(worker=worker, stores=job_stores, queue=queue, reporter=reporter)


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
