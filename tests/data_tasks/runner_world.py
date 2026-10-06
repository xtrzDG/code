"""
An in-memory world for the data-task runner: tables of numbered rows a
fake batch adapter walks in keyset order, a clock each batch moves, worker
pulses and the runner's lock.
"""

from collections.abc import Callable, Sequence
from threading import Event

from typed_time_provider import Microseconds, WallClock

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.contracts.data_tasks import DataTaskRegistryContract
from app.gateways.worker.periodic.run_data_tasks import RUN_DATA_TASKS_JOB
from app.registries.locks.data_task_lock_registry import DataTaskLockRegistry
from app.repositories.data_task_state_repository import DataTaskStateRepository
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.data_tasks import DataTaskBatchRequest, DataTaskBatchResult
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.maintenance.constrained_integers import (
    DataTaskBatchSize,
    DataTaskRunSeconds,
)
from app.schemas.typings.maintenance.constrained_strings import (
    DataTaskKey,
    DataTaskPosition,
)
from app.schemas.typings.platform.constrained_strings import JobName, ReleaseVersion
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.use_cases.maintenance.data_tasks.run_data_tasks_use_case import (
    RunDataTasksUseCase,
)
from tests.data_tasks.data_task_support import NOW, RELEASE, SECOND, data_task_states


def position_of(row: int) -> DataTaskPosition:
    return DataTaskPosition(f"row-{row:06d}")


def row_of(position: DataTaskPosition | None) -> int:
    return -1 if position is None else int(str(position).removeprefix("row-"))


class SteppingClock:
    """A wall clock that each batch moves by `batch_step` microseconds."""

    def __init__(self) -> None:
        self.now: int = NOW
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )


class TableBatches:
    """
    The batch adapter over numbered rows per task: a batch takes the next
    `batch_size` rows after the position; rows in `broken` cannot be
    upgraded; `fail_next` makes the next batches fail as a whole.
    """

    def __init__(self, clock: SteppingClock, batch_step: int = SECOND) -> None:
        self.rows: dict[str, int] = {}
        self.broken: set[int] = set()
        self.fail_next: int = 0
        self.requests: list[DataTaskBatchRequest] = []
        self.before_batch: Callable[[], None] = lambda: None
        self._clock: SteppingClock = clock
        self._batch_step: int = batch_step

    def run_batch(self, request: DataTaskBatchRequest) -> DataTaskBatchResult:
        self.before_batch()
        self.requests.append(request)
        self._clock.now += self._batch_step
        if self.fail_next:
            self.fail_next -= 1
            raise ExternalServiceError("The database did not answer in time.")

        total: int = self.rows.get(str(request.task.key), 0)
        first: int = row_of(request.after) + 1
        last: int = min(total, first + int(request.batch_size)) - 1
        taken: range = range(first, last + 1)
        failed: list[int] = [row for row in taken if row in self.broken]
        return DataTaskBatchResult(
            next_position=position_of(last) if last + 1 < total else None,
            scanned=DocumentCount(len(taken)),
            changed=DocumentCount(len(taken) - len(failed)),
            failed_document_keys=[StoredDocumentKey(f"doc_{row}") for row in failed],
        )


class Pulses:
    """Worker pulses the test adds; the runner reads those of its window."""

    def __init__(self) -> None:
        self.pulses: list[WorkerHeartbeatDocument] = []

    def list_pulses_since(self, since: Microseconds) -> list[WorkerHeartbeatDocument]:
        return [pulse for pulse in self.pulses if int(pulse.beat_at) >= int(since)]


class RunnerWorld:
    """The runner over one registry, with the collaborators a test steers."""

    def __init__(
        self,
        registry: DataTaskRegistryContract,
        release: ReleaseVersion | None = RELEASE,
        batch_size: int = 5_000,
        run_seconds: int = 240,
        batch_step: int = SECOND,
        locks: InMemoryAdvisoryLockAdapter | None = None,
        states: DataTaskStateRepository | None = None,
    ) -> None:
        self.clock = SteppingClock()
        self.batches = TableBatches(self.clock, batch_step)
        self.states = data_task_states() if states is None else states
        self.pulses = Pulses()
        self.locks = InMemoryAdvisoryLockAdapter() if locks is None else locks
        self.runner = RunDataTasksUseCase(
            registry=registry,
            state_repo=self.states,
            batches=self.batches,
            locks=DataTaskLockRegistry(self.locks),
            pulse_repo=self.pulses,
            wall_clock=self.clock.wall_clock,
            release=release,
            batch_size=DataTaskBatchSize(batch_size),
            run_seconds=DataTaskRunSeconds(run_seconds),
        )

    def beat(self, pulses: Sequence[WorkerHeartbeatDocument]) -> None:
        self.pulses.pulses.extend(pulses)

    def run(self) -> JobReport:
        return self.runner.run(
            JobTick(
                job_name=JobName(str(RUN_DATA_TASKS_JOB)),
                scheduled_at=self.clock.wall_clock.now_unix(),
            )
        )

    def state(self, key: str) -> DataTaskStateDocument:
        found = self.states.get_many([DataTaskKey(key)])
        assert len(found) == 1, f"No state of {key}."
        return found[0]


def pause_inside_a_batch(batches: TableBatches) -> tuple[Event, Event]:
    """
    Events to hold one runner inside its first batch: `inside` is set once
    it is there, and it goes on when the test sets `release`.
    """

    inside, release = Event(), Event()

    def hold() -> None:
        if not inside.is_set():
            inside.set()
            assert release.wait(timeout=10)

    batches.before_batch = hold
    return inside, release
