"""
The data-task card of the admin system page: each registry task with its
stored progress, the table's estimated rows, open tasks first.
"""

from collections.abc import Mapping, Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import DataTaskStatus
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import DataTaskDefinition, DataTaskView
from app.schemas.typings.maintenance.constrained_integers import (
    DataTaskBatchCount,
    DataTaskFailureCount,
)
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.monitoring.constrained_integers import CollectionRowEstimate
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.maintenance.data_task_status import (
    effective_status,
    is_current_target,
    is_stalled,
)

# Open tasks first (the failed ones on top), then the finished ones.
STATUS_ORDER: Mapping[DataTaskStatus, int] = {
    DataTaskStatus.FAILED: 0,
    DataTaskStatus.RUNNING: 1,
    DataTaskStatus.PENDING: 2,
    DataTaskStatus.DONE: 3,
}
NO_ROWS: DocumentCount = DocumentCount(0)


def build_data_task_view(
    task: DataTaskDefinition,
    state: DataTaskStateDocument | None,
    row_estimates: Mapping[str, CollectionRowEstimate],
    now: Microseconds,
) -> DataTaskView:
    """A task as the card shows it; a state of an older target counts as none."""

    current: DataTaskStateDocument | None = (
        state if is_current_target(task, state) else None
    )
    status: DataTaskStatus = effective_status(task, state)
    return DataTaskView(
        key=task.key,
        kind=task.kind,
        collection_name=task.collection_name,
        field=task.field,
        target_version=task.target_version,
        status=status,
        lists=list(task.lists),
        scanned_count=NO_ROWS if current is None else current.scanned_count,
        changed_count=NO_ROWS if current is None else current.changed_count,
        failed_row_count=NO_ROWS if current is None else current.failed_row_count,
        failed_document_keys=[] if current is None else current.failed_document_keys,
        row_estimate=row_estimates.get(str(task.collection_name)),
        batch_count=DataTaskBatchCount(0) if current is None else current.batch_count,
        pending_since=None
        if current is None or status is DataTaskStatus.DONE
        else current.pending_since,
        started_at=None if current is None else current.started_at,
        last_batch_at=None if current is None else current.last_batch_at,
        finished_at=None if current is None else current.finished_at,
        failure_count=DataTaskFailureCount(0)
        if current is None
        else current.failure_count,
        last_error=None if current is None else current.last_error,
        is_stalled=is_stalled(task, state, now),
    )


def build_data_task_views(
    tasks: Sequence[DataTaskDefinition],
    states: Mapping[DataTaskKey, DataTaskStateDocument],
    row_estimates: Mapping[str, CollectionRowEstimate],
    now: Microseconds,
) -> list[DataTaskView]:
    """Every task, open ones first, in registry order within a status."""

    views: list[DataTaskView] = [
        build_data_task_view(task, states.get(task.key), row_estimates, now)
        for task in tasks
    ]
    return sorted(views, key=lambda view: STATUS_ORDER[view.status])
