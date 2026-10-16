"""
Whether a cabinet list may still miss rows written before a release: some
post-deploy data task that fills what the list pages by (a lookup column
of older rows, documents of an older shape) is not done yet. The list then
says it is still indexing (`is_indexing` of its page).
"""

from app.contracts.data_tasks import DataTaskRegistryContract, DataTaskStateRepoContract
from app.schemas.constants.maintenance import IndexedList
from app.schemas.dto.data_tasks import DataTaskDefinition
from app.schemas.typings.maintenance.booleans import IsListIndexing
from app.utilities.maintenance.data_task_status import is_list_indexing


def read_list_indexing(
    registry: DataTaskRegistryContract,
    state_repo: DataTaskStateRepoContract,
    indexed_list: IndexedList,
) -> IsListIndexing:
    """One keyed read of the few task states the list depends on."""

    tasks: list[DataTaskDefinition] = registry.tasks_for_list(indexed_list)
    if not tasks:
        return False

    return is_list_indexing(tasks, state_repo.get_many([task.key for task in tasks]))
