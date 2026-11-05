import logging
from contextlib import ExitStack

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.data_tasks import (
    DataTaskBatchAdapterContract,
    DataTaskLockRegistryContract,
    DataTaskRegistryContract,
    DataTaskStateRepoContract,
    WorkerPulseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.maintenance import DataTaskStatus
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import (
    DataTaskBatchRequest,
    DataTaskBatchResult,
    DataTaskDefinition,
    RolloutView,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.maintenance.constrained_integers import (
    DataTaskBatchSize,
    DataTaskRunSeconds,
)
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.utilities.maintenance.data_task_progress import (
    after_batch,
    after_failed_batch,
    new_state,
    walk_again,
)
from app.utilities.maintenance.data_task_status import (
    is_current_target,
    states_by_key,
)
from app.utilities.maintenance.rollout_overlap import (
    read_rollout,
    rollout_window_start,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
DATA_TASK_BATCH_SIZE: DataTaskBatchSize = DataTaskBatchSize(5_000)
# The job runs every 5 minutes; a run starts no batch after this long, so
# two runs never overlap and the batch worker's other jobs get their turn.
DATA_TASK_RUN_SECONDS: DataTaskRunSeconds = DataTaskRunSeconds(4 * 60)


class RunDataTasksUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The post-deploy data tasks run themselves (the `run_data_tasks` job of
    the batch worker, every 5 minutes): once no worker of another release
    has beaten for the settling window (the release overlap is over), it
    walks every open task of the registry in keyset batches of 5,000 rows,
    each a short transaction of its own, and stores the task's progress
    after every batch, so a restart goes on where it stopped.

    One process runs them at a time (a lock; a run that finds it taken
    leaves the turn to the holder). A run first records every task it has
    not seen for its current target (a new collection version, a new
    column) as pending since now. A batch that fails as a whole is
    recorded and tried again on the next run; a walk that ends with rows a
    migration could not upgrade leaves the task FAILED, walked again once
    a new release runs (or a platform admin asks). A run starts no batch
    after `run_seconds`; the rest waits for the next run.
    """

    def __init__(
        self,
        registry: DataTaskRegistryContract,
        state_repo: DataTaskStateRepoContract,
        batches: DataTaskBatchAdapterContract,
        locks: DataTaskLockRegistryContract,
        pulse_repo: WorkerPulseRepoContract,
        wall_clock: WallClock[Microseconds],
        release: ReleaseVersion | None,
        batch_size: DataTaskBatchSize = DATA_TASK_BATCH_SIZE,
        run_seconds: DataTaskRunSeconds = DATA_TASK_RUN_SECONDS,
    ) -> None:
        self._registry: DataTaskRegistryContract = registry
        self._state_repo: DataTaskStateRepoContract = state_repo
        self._batches: DataTaskBatchAdapterContract = batches
        self._locks: DataTaskLockRegistryContract = locks
        self._pulse_repo: WorkerPulseRepoContract = pulse_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._release: ReleaseVersion | None = release
        self._batch_size: DataTaskBatchSize = batch_size
        self._run_seconds: DataTaskRunSeconds = run_seconds

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        with ExitStack() as held:
            try:
                held.enter_context(self._locks.lock_runner())
            except ExternalServiceError:
                LOGGER.info("Data tasks: another process runs them; skipped.")
                return JobReport()

            return JobReport(processed_count=ProcessedItemCount(self._run_locked()))

    def _run_locked(self) -> int:
        now: Microseconds = self._wall_clock.now_unix()
        tasks: list[DataTaskDefinition] = self._registry.list_tasks()
        states: dict[DataTaskKey, DataTaskStateDocument] = self._current_states(
            tasks, now
        )
        rollout: RolloutView = read_rollout(
            self._pulse_repo.list_pulses_since(rollout_window_start(now)),
            self._release,
            now,
        )
        if not rollout.is_settled:
            LOGGER.info(
                "Data tasks wait for the release overlap to end (workers of %s "
                "still beat).",
                ", ".join(str(release) for release in rollout.other_releases)
                or "an unnamed release",
            )
            return 0

        deadline: Microseconds = self._wall_clock.now_unix_with_delta(
            Seconds(int(self._run_seconds))
        )
        scanned: int = 0
        for task in tasks:
            if not self._is_before(deadline):
                break

            state: DataTaskStateDocument = states[task.key]
            if state.status in {DataTaskStatus.DONE, DataTaskStatus.FAILED}:
                continue

            scanned += self._walk(task, state, deadline)

        return scanned

    def _current_states(
        self,
        tasks: list[DataTaskDefinition],
        now: Microseconds,
    ) -> dict[DataTaskKey, DataTaskStateDocument]:
        """
        Every task's state for its current target, stored when it is new:
        first seen, a newer collection version, or a failed walk that a
        new release walks again.
        """

        stored: dict[DataTaskKey, DataTaskStateDocument] = states_by_key(
            self._state_repo.get_many([task.key for task in tasks])
        )
        states: dict[DataTaskKey, DataTaskStateDocument] = {}
        for task in tasks:
            state: DataTaskStateDocument | None = stored.get(task.key)
            current: DataTaskStateDocument
            if state is None or not is_current_target(task, state):
                current = new_state(task, now)
            elif state.status is DataTaskStatus.FAILED and state.release != (
                self._release
            ):
                current = walk_again(task, state, now)
            else:
                current = state

            if current is not state:
                self._state_repo.save(current)
            states[task.key] = current

        return states

    def _walk(
        self,
        task: DataTaskDefinition,
        state: DataTaskStateDocument,
        deadline: Microseconds,
    ) -> int:
        """Batches of one task until it ends, fails or the run's time is up."""

        scanned: int = 0
        while self._is_before(deadline):
            try:
                result: DataTaskBatchResult = self._batches.run_batch(
                    DataTaskBatchRequest(
                        task=task, after=state.position, batch_size=self._batch_size
                    )
                )
            except ApplicationError as error:
                state = after_failed_batch(
                    state, error, self._wall_clock.now_unix(), self._release
                )
                self._state_repo.save(state)
                LOGGER.warning(
                    "Data task %s: a batch failed (%s); the next run tries it again.",
                    task.key,
                    type(error).__name__,
                )
                return scanned

            state = after_batch(
                state, result, self._wall_clock.now_unix(), self._release
            )
            self._state_repo.save(state)
            scanned += int(result.scanned)
            if state.status is not DataTaskStatus.RUNNING:
                LOGGER.info(
                    "Data task %s %s: %d rows looked at, %d changed, %d failed, "
                    "%d batches.",
                    task.key,
                    state.status.value,
                    int(state.scanned_count),
                    int(state.changed_count),
                    int(state.failed_row_count),
                    int(state.batch_count),
                )
                break

        return scanned

    def _is_before(self, deadline: Microseconds) -> bool:
        return int(self._wall_clock.now_unix()) < int(deadline)
