"""
The state transitions of one post-deploy data task: first seen, started
again for a new target or release, after a batch that worked, after one
that failed, and asked again by a platform admin. Pure functions over
`DataTaskStateDocument`.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import DataTaskStatus
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import DataTaskBatchResult, DataTaskDefinition
from app.schemas.typings.maintenance.constrained_integers import (
    DataTaskBatchCount,
    DataTaskFailureCount,
)
from app.schemas.typings.maintenance.constrained_strings import DataTaskErrorText
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.storage.constrained_integers import DocumentCount

# A state lists at most this many rows that could not be upgraded.
LISTED_FAILURES: int = 20
ERROR_TEXT_LIMIT: int = 500


def new_state(
    task: DataTaskDefinition,
    now: Microseconds,
    pending_since: Microseconds | None = None,
) -> DataTaskStateDocument:
    """A pending task at the start of a walk (its target as the registry has it)."""

    return DataTaskStateDocument(
        key=task.key,
        kind=task.kind,
        collection_name=task.collection_name,
        field=task.field,
        target_version=task.target_version,
        status=DataTaskStatus.PENDING,
        pending_since=now if pending_since is None else pending_since,
        created_at=now,
        updated_at=now,
    )


def after_batch(
    state: DataTaskStateDocument,
    result: DataTaskBatchResult,
    now: Microseconds,
    release: ReleaseVersion | None,
) -> DataTaskStateDocument:
    """
    The walk moved on: RUNNING while rows are left; at its end DONE, or
    FAILED when some rows of the walk could not be upgraded.
    """

    failed_rows: int = int(state.failed_row_count) + len(result.failed_document_keys)
    is_finished: bool = result.next_position is None
    status: DataTaskStatus = (
        DataTaskStatus.RUNNING
        if not is_finished
        else DataTaskStatus.FAILED
        if failed_rows
        else DataTaskStatus.DONE
    )
    return state.model_copy(
        update={
            "status": status,
            "position": result.next_position,
            "scanned_count": DocumentCount(
                int(state.scanned_count) + int(result.scanned)
            ),
            "changed_count": DocumentCount(
                int(state.changed_count) + int(result.changed)
            ),
            "failed_row_count": DocumentCount(failed_rows),
            "failed_document_keys": [
                *state.failed_document_keys,
                *result.failed_document_keys,
            ][:LISTED_FAILURES],
            "batch_count": DataTaskBatchCount(int(state.batch_count) + 1),
            "started_at": state.started_at or now,
            "last_batch_at": now,
            "finished_at": now if is_finished else None,
            "failure_count": DataTaskFailureCount(0),
            "last_error": None,
            "release": release,
            "updated_at": now,
        }
    )


def after_failed_batch(
    state: DataTaskStateDocument,
    error: Exception,
    now: Microseconds,
    release: ReleaseVersion | None,
) -> DataTaskStateDocument:
    """
    A batch failed as a whole (nothing of it was written): the walk stays
    where it was and the next run tries the same batch again.
    """

    text: str = f"{type(error).__name__}: {error}".strip()[:ERROR_TEXT_LIMIT]
    return state.model_copy(
        update={
            "status": DataTaskStatus.RUNNING
            if state.position is not None
            else state.status,
            "started_at": state.started_at or now,
            "failure_count": DataTaskFailureCount(int(state.failure_count) + 1),
            "last_error": DataTaskErrorText(text),
            "release": release,
            "updated_at": now,
        }
    )


def walk_again(
    task: DataTaskDefinition, state: DataTaskStateDocument, now: Microseconds
) -> DataTaskStateDocument:
    """
    A failed task walks its table again from the start (a new release may
    have fixed the upcaster; a platform admin asked); it stays due since
    it first became due, so the stall alert keeps counting.
    """

    return new_state(task, now, pending_since=state.pending_since).model_copy(
        update={"created_at": state.created_at}
    )
