"""
How far the post-deploy data tasks are, from the registry's definitions
and their stored states: shared by the runner, the admin card, readiness,
the BACKFILL_STALLED alert and the cabinet's lists.
"""

from collections.abc import Mapping, Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import (
    DataTaskKind,
    DataTaskStatus,
)
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import DataTaskDefinition, DataTaskSummary
from app.schemas.typings.maintenance.booleans import (
    IsDataTaskStalled,
    IsListIndexing,
)
from app.schemas.typings.maintenance.constrained_integers import DataTaskCount
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey

MICROSECONDS_PER_HOUR: int = 60 * 60 * 1_000_000
# A task not done this long after it became due fires BACKFILL_STALLED
# (ops/alerts/backfill_stalled.yaml).
STALL_HOURS: int = 24


def is_current_target(
    task: DataTaskDefinition, state: DataTaskStateDocument | None
) -> bool:
    """
    The stored state is of this task's current target: a document
    migration stored for an older schema version is pending again.
    """

    if state is None:
        return False

    return task.kind is not DataTaskKind.MIGRATE_DOCUMENTS or (
        state.target_version == task.target_version
    )


def effective_status(
    task: DataTaskDefinition, state: DataTaskStateDocument | None
) -> DataTaskStatus:
    """PENDING without a state of the current target, else the stored status."""

    if state is None or not is_current_target(task, state):
        return DataTaskStatus.PENDING

    return state.status


def is_stalled(
    task: DataTaskDefinition,
    state: DataTaskStateDocument | None,
    now: Microseconds,
) -> IsDataTaskStalled:
    """Not done more than STALL_HOURS after it became due."""

    if state is None or not is_current_target(task, state):
        return False

    if state.status is DataTaskStatus.DONE:
        return False

    return int(now) - int(state.pending_since) > STALL_HOURS * MICROSECONDS_PER_HOUR


def states_by_key(
    states: Sequence[DataTaskStateDocument],
) -> dict[DataTaskKey, DataTaskStateDocument]:
    return {state.key: state for state in states}


def summarize_data_tasks(
    tasks: Sequence[DataTaskDefinition],
    states: Mapping[DataTaskKey, DataTaskStateDocument],
    now: Microseconds,
) -> DataTaskSummary:
    """Open (not done), failed and stalled tasks."""

    open_tasks: list[DataTaskDefinition] = [
        task
        for task in tasks
        if effective_status(task, states.get(task.key)) is not DataTaskStatus.DONE
    ]
    return DataTaskSummary(
        open_count=DataTaskCount(len(open_tasks)),
        failed_count=DataTaskCount(
            sum(
                1
                for task in open_tasks
                if effective_status(task, states.get(task.key)) is DataTaskStatus.FAILED
            )
        ),
        stalled_count=DataTaskCount(
            sum(1 for task in open_tasks if is_stalled(task, states.get(task.key), now))
        ),
    )


def is_list_indexing(
    tasks: Sequence[DataTaskDefinition],
    states: Sequence[DataTaskStateDocument],
) -> IsListIndexing:
    """Some task that fills what a list pages by is not done yet."""

    stored: dict[DataTaskKey, DataTaskStateDocument] = states_by_key(states)
    return any(
        effective_status(task, stored.get(task.key)) is not DataTaskStatus.DONE
        for task in tasks
    )
