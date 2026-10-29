"""
The data-task line of GET /readyz: how many post-deploy data tasks of this
release are still open. The deploy guard (deploy-smoke.yml) reads it from
production before it promotes the next release.
"""

import logging

from typed_time_provider import Microseconds

from app.contracts.data_tasks import DataTaskRegistryContract, DataTaskStateRepoContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.observability import HealthCheckStatus
from app.schemas.dto.data_tasks import DataTaskDefinition, DataTaskSummary
from app.schemas.dto.health import DataTasksCheck
from app.schemas.exceptions.base_exception import ApplicationError
from app.utilities.maintenance.data_task_status import (
    states_by_key,
    summarize_data_tasks,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


def check_data_tasks(
    registry: DataTaskRegistryContract,
    state_repo: DataTaskStateRepoContract,
    storage_scope: StorageScopeContract,
    now: Microseconds,
) -> DataTasksCheck:
    """
    OK when every task is done, DEGRADED while some are open (never a
    reason to stop traffic), SKIPPED when their states cannot be read.
    """

    tasks: list[DataTaskDefinition] = registry.list_tasks()
    try:
        with storage_scope.platform_wide():
            summary: DataTaskSummary = summarize_data_tasks(
                tasks,
                states_by_key(state_repo.get_many([task.key for task in tasks])),
                now,
            )
    except ApplicationError as error:
        LOGGER.warning("Data task states cannot be read: %s", error)
        return DataTasksCheck(status=HealthCheckStatus.SKIPPED)

    return DataTasksCheck(
        status=HealthCheckStatus.OK
        if int(summary.open_count) == 0
        else HealthCheckStatus.DEGRADED,
        open=summary.open_count,
        failed=summary.failed_count,
        stalled=summary.stalled_count,
    )
