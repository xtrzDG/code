import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.data_tasks import (
    DataTaskRegistryContract,
    DataTaskStateRepoContract,
    WorkerPulseRepoContract,
)
from app.contracts.monitoring import DatabaseSizeAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.data_tasks import (
    DataTaskDefinition,
    DataTasksQuery,
    DataTaskSummary,
    DataTasksView,
)
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_health import DatabaseSize
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.maintenance.constrained_integers import DataTaskBatchSize
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.monitoring.constrained_integers import CollectionRowEstimate
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.use_cases.admin.system.data_task_views import build_data_task_views
from app.utilities.maintenance.data_task_status import (
    states_by_key,
    summarize_data_tasks,
)
from app.utilities.maintenance.rollout_overlap import (
    read_rollout,
    rollout_window_start,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class GetDataTasksUseCase(UseCaseContract[DataTasksQuery, DataTasksView]):
    """
    GET /v1/admin/system/data-tasks: the post-deploy data tasks for the
    platform admin's system page. Every task of this release's registry
    with its progress against the table's estimated rows, the open,
    failed and stalled counts, and whether the release overlap is over
    (the batch worker starts only then). One keyed read of the tasks'
    states, the worker pulses of the settling window and the database
    catalog (left out when it cannot be read).
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        registry: DataTaskRegistryContract,
        state_repo: DataTaskStateRepoContract,
        pulse_repo: WorkerPulseRepoContract,
        database_size: DatabaseSizeAdapterContract,
        wall_clock: WallClock[Microseconds],
        release: ReleaseVersion | None,
        batch_size: DataTaskBatchSize,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._registry: DataTaskRegistryContract = registry
        self._state_repo: DataTaskStateRepoContract = state_repo
        self._pulse_repo: WorkerPulseRepoContract = pulse_repo
        self._database_size: DatabaseSizeAdapterContract = database_size
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._release: ReleaseVersion | None = release
        self._batch_size: DataTaskBatchSize = batch_size

    def run(self, input_data: DataTasksQuery) -> DataTasksView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        tasks: list[DataTaskDefinition] = self._registry.list_tasks()
        states: dict[DataTaskKey, DataTaskStateDocument] = states_by_key(
            self._state_repo.get_many([task.key for task in tasks])
        )
        summary: DataTaskSummary = summarize_data_tasks(tasks, states, now)
        return DataTasksView(
            checked_at=now,
            batch_size=self._batch_size,
            rollout=read_rollout(
                self._pulse_repo.list_pulses_since(rollout_window_start(now)),
                self._release,
                now,
            ),
            open_count=summary.open_count,
            failed_count=summary.failed_count,
            stalled_count=summary.stalled_count,
            tasks=build_data_task_views(tasks, states, self._row_estimates(), now),
        )

    def _row_estimates(self) -> dict[str, CollectionRowEstimate]:
        try:
            size: DatabaseSize | None = self._database_size.measure()
        except ApplicationError as error:
            LOGGER.warning("Table sizes for the data tasks were not read: %s", error)
            return {}

        if size is None:
            return {}

        # The catalog names tables with their schema ("workshop.contacts");
        # a task names the collection, which is the bare table name.
        return {
            str(table.table).rpartition(".")[2]: table.row_estimate
            for table in size.tables
        }
