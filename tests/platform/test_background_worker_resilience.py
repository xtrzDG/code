"""The background worker keeps going when its queue, a tick or a daily job fails."""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.in_memory_queued_job_claim_adapter import (
    InMemoryQueuedJobClaimAdapter,
)
from app.gateways.worker.background_worker import (
    BackgroundWorker,
    PeriodicJobSpec,
)
from app.repositories.job_repositories import QueuedJobRepository
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import ExpiredLeaseRelease, JobClaimRequest
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    JobIntervalSeconds,
    ProcessedItemCount,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    CountingPeriodicOperator,
    CountingStopEvent,
    FlakyQueuedOperator,
    build_job_stores,
    build_worker,
)


class UnreachableQueueRepository(QueuedJobRepository):
    """A queue that fails on the first reads, as during a Postgres restart."""

    def __init__(self, failing_reads: int, error: Exception) -> None:
        jobs = InMemoryDocumentCollectionAdapter[QueuedJobDocument](QueuedJobDocument)
        super().__init__(jobs, InMemoryQueuedJobClaimAdapter(jobs))
        self.reads: int = 0
        self._failing_reads: int = failing_reads
        self._error: Exception = error

    def claim_due(self, claim: JobClaimRequest) -> list[QueuedJobDocument]:
        self._read()
        return super().claim_due(claim)

    def release_expired_leases(
        self, release: ExpiredLeaseRelease
    ) -> list[QueuedJobDocument]:
        self._read()
        return super().release_expired_leases(release)

    def _read(self) -> None:
        self.reads += 1
        if self.reads <= self._failing_reads:
            raise self._error


def test_an_unreachable_queue_does_not_stop_the_worker() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    stores.job_repo = UnreachableQueueRepository(
        failing_reads=2, error=RuntimeError("connection refused")
    )
    hourly = CountingPeriodicOperator()
    operator = FlakyQueuedOperator(failures_before_success=0)
    kit = build_worker(
        clock,
        [
            PeriodicJobSpec(
                name=JobName("end_trials"),
                interval_seconds=JobIntervalSeconds(3600),
                operator=hourly,
            )
        ],
        {RUN_AUTOTESTS: operator},
        stores=stores,
    )
    kit.queue.enqueue(RUN_AUTOTESTS, JobPayloadJson("{}"), business_id=None)

    first = kit.worker.run_once()
    second = kit.worker.run_once()

    # The reaper and the first lane failed; the periodic job still ran.
    assert (first.periodic_runs, first.queued_runs, first.failures) == (1, 1, 2)
    assert (second.periodic_runs, second.queued_runs, second.failures) == (0, 0, 0)
    assert len(hourly.ticks) == 1
    assert len(operator.calls) == 1
    assert [str(error) for error in kit.reporter.errors] == ["connection refused"] * 2


class ExplodingWorker(BackgroundWorker):
    """A tick that fails as a whole, as when the error reporter itself fails."""

    def __init__(self, worker: BackgroundWorker, failing_ticks: int) -> None:
        self.__dict__.update(worker.__dict__)
        self.ticks: int = 0
        self._failing_ticks: int = failing_ticks

    def run_periodic_tick(self) -> tuple[int, int]:
        self.ticks += 1
        if self.ticks <= self._failing_ticks:
            raise ExternalServiceError("database is down")

        return super().run_periodic_tick()


def test_failed_ticks_back_off_and_the_worker_keeps_ticking() -> None:
    clock = ControlledClock()
    kit = build_worker(clock, [])
    exploding = ExplodingWorker(kit.worker, failing_ticks=3)
    stop_event = CountingStopEvent(ticks=5)

    exploding.run_forever(stop_event)

    assert exploding.ticks == 5
    assert stop_event.pauses == [10, 20, 40, 5, 5]
    assert kit.reporter.errors == []  # application errors are logged, not reported


def test_a_failed_daily_job_is_retried_within_minutes() -> None:
    clock = ControlledClock()
    flaky = FlakyPeriodicOperator(failures_before_success=1)
    kit = build_worker(
        clock,
        [
            PeriodicJobSpec(
                name=JobName("purge_expired_recordings"),
                interval_seconds=JobIntervalSeconds(86_400),
                operator=flaky,
            )
        ],
    )

    failed = kit.worker.run_once()
    clock.advance(60)
    too_soon = kit.worker.run_once()
    clock.advance(5 * 60)
    retried = kit.worker.run_once()
    clock.advance(60 * 60)
    next_hour = kit.worker.run_once()

    assert (failed.periodic_runs, failed.failures) == (1, 1)
    assert too_soon.periodic_runs == 0
    assert (retried.periodic_runs, retried.failures) == (1, 0)
    assert next_hour.periodic_runs == 0  # once per day after success
    assert len(kit.reporter.errors) == 1
    run = kit.stores.periodic_run_repo.get(
        JobName("purge_expired_recordings"),
        PeriodicJobSpec(
            name=JobName("purge_expired_recordings"),
            interval_seconds=JobIntervalSeconds(86_400),
            operator=flaky,
        ).period_key(clock.wall_clock().now_unix()),
    )
    assert run is not None
    assert (run.status.value, run.attempts, run.last_error) == ("succeeded", 2, None)


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
