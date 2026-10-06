"""
Post-deploy data tasks: the registry's entries, one keyset batch, and how
the platform admin, readiness and the cabinet's lists see them
(docs/operations/deploys.md, "Data tasks after a deploy").
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import (
    DataTaskKind,
    DataTaskStatus,
    IndexedList,
)
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.maintenance.booleans import (
    IsDataTaskStalled,
    IsRolloutSettled,
)
from app.schemas.typings.maintenance.constrained_integers import (
    DataTaskBatchCount,
    DataTaskBatchSize,
    DataTaskCount,
    DataTaskFailureCount,
)
from app.schemas.typings.maintenance.constrained_strings import (
    DataTaskErrorText,
    DataTaskKey,
    DataTaskPosition,
)
from app.schemas.typings.maintenance.strings import NoBackfillReason
from app.schemas.typings.monitoring.constrained_integers import CollectionRowEstimate
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
    SchemaMigrationName,
)
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.schemas.typings.users.prefixed_id import UserId


class DataTaskDefinition(ImmutableDTO):
    """
    One entry of the data-task registry: a document migration of a
    collection to `target_version`, or the backfill of one trigger-kept
    lookup column (`field`). `lists` are the cabinet lists that read what
    the task fills.
    """

    key: DataTaskKey
    kind: DataTaskKind
    collection_name: DocumentCollectionName
    field: DocumentFieldPath | None = None
    target_version: DocumentSchemaVersionNumber | None = None
    lists: list[IndexedList] = Field(default_factory=list[IndexedList])


class LookupBackfillDeclaration(ImmutableDTO):
    """
    A trigger-kept lookup column that `migration` added to a table which
    already held rows: a backfill task fills it for those rows. `lists`
    page by it.
    """

    collection_name: DocumentCollectionName
    field: DocumentFieldPath
    migration: SchemaMigrationName
    lists: list[IndexedList] = Field(default_factory=list[IndexedList])


class LookupColumnWithoutBackfill(ImmutableDTO):
    """
    A lookup column `migration` added to an existing table whose older rows
    cannot hold the field, so nothing is filled (`reason` says why).
    """

    collection_name: DocumentCollectionName
    field: DocumentFieldPath
    migration: SchemaMigrationName
    reason: NoBackfillReason


class DataTaskBatchRequest(ImmutableDTO):
    """The next batch of a task's walk: the rows after `after` (None: the first)."""

    task: DataTaskDefinition
    after: DataTaskPosition | None = None
    batch_size: DataTaskBatchSize


class DataTaskBatchResult(ImmutableDTO):
    """
    What one batch did: the rows it looked at, those it rewrote or filled,
    the rows a migration could not upgrade, and where the next batch starts
    (None: the walk reached the end).
    """

    next_position: DataTaskPosition | None = None
    scanned: DocumentCount
    changed: DocumentCount
    failed_document_keys: list[StoredDocumentKey] = Field(
        default_factory=list[StoredDocumentKey]
    )


class RolloutView(ImmutableDTO):
    """
    Whether the release overlap is over: no worker of another release beat
    within the settling window. `other_releases` are those still seen and
    `settles_at` is when the last of their pulses leaves the window.
    """

    is_settled: IsRolloutSettled
    release: ReleaseVersion | None = None
    other_releases: list[ReleaseVersion] = Field(default_factory=list[ReleaseVersion])
    settles_at: Microseconds | None = None


class DataTaskView(ImmutableDTO):
    """
    One data task as the platform admin sees it: its state, the progress of
    the current walk against the table's estimated rows, and its failures.
    `pending_since` is set while it is not done; `is_stalled` once that has
    lasted more than 24 hours (the BACKFILL_STALLED alert).
    """

    key: DataTaskKey
    kind: DataTaskKind
    collection_name: DocumentCollectionName
    field: DocumentFieldPath | None = None
    target_version: DocumentSchemaVersionNumber | None = None
    status: DataTaskStatus
    lists: list[IndexedList]
    scanned_count: DocumentCount
    changed_count: DocumentCount
    failed_row_count: DocumentCount
    failed_document_keys: list[StoredDocumentKey]
    row_estimate: CollectionRowEstimate | None = None
    batch_count: DataTaskBatchCount
    pending_since: Microseconds | None = None
    started_at: Microseconds | None = None
    last_batch_at: Microseconds | None = None
    finished_at: Microseconds | None = None
    failure_count: DataTaskFailureCount
    last_error: DataTaskErrorText | None = None
    is_stalled: IsDataTaskStalled


class DataTasksQuery(ImmutableDTO):
    """GET /v1/admin/system/data-tasks by a platform admin."""

    user_id: UserId


class DataTasksView(ImmutableDTO):
    """
    The post-deploy data tasks at `checked_at`: in batches of how many rows
    the batch worker runs them, whether the release overlap is over, the
    counts the deploy guard and the alert read, and every task (open ones
    first).
    """

    checked_at: Microseconds
    batch_size: DataTaskBatchSize
    rollout: RolloutView
    open_count: DataTaskCount
    failed_count: DataTaskCount
    stalled_count: DataTaskCount
    tasks: list[DataTaskView]


class DataTaskSummary(ImmutableDTO):
    """
    The data tasks in three figures and the lists they keep incomplete:
    `open_count` is every task not done yet (failed ones included), as
    `GET /readyz` reports it to the deploy guard.
    """

    open_count: DataTaskCount
    failed_count: DataTaskCount
    stalled_count: DataTaskCount
    indexing_lists: list[IndexedList] = Field(default_factory=list[IndexedList])


class RetryDataTaskCommand(ImmutableDTO):
    """POST /v1/admin/system/data-tasks/{task_key}/retry by a platform admin."""

    user_id: UserId
    key: DataTaskKey
    client_ip_address: ClientIpAddress | None = None


class RetryDataTaskResult(ImmutableDTO):
    """The task after the retry, and the audit entry that records it."""

    task: DataTaskView
    audit_log_entry_id: AuditLogEntryId
