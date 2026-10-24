from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import DataTaskKind, DataTaskStatus
from app.schemas.typings.maintenance.constrained_integers import (
    DataTaskBatchCount,
    DataTaskFailureCount,
)
from app.schemas.typings.maintenance.constrained_strings import (
    DataTaskErrorText,
    DataTaskKey,
    DataTaskPosition,
)
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.schemas.typings.storage.strings import StoredDocumentKey


class DataTaskStateDocument(BaseDocument):
    """
    The progress of one post-deploy data task (the maintenance state, a
    platform collection stored under the task's `key`), written by the
    batch worker after every keyset batch, so a restart goes on where the
    last batch stopped.

    `target_version` is the schema version a document migration rewrites
    to: a later release with a newer version starts the task again.
    `pending_since` is when the task last became pending for its target
    (the BACKFILL_STALLED alert fires 24 hours later if it is not done);
    `position` is where the walk stopped (None before the first batch and
    after the last). The counts are of the current walk; `failure_count`
    counts batches that failed in a row and `last_error` says why the last
    one did. `failed_document_keys` names the first rows a migration could
    not upgrade (never their content). `release` is the build whose worker
    ran the last batch.
    """

    key: DataTaskKey
    kind: DataTaskKind
    collection_name: DocumentCollectionName
    field: DocumentFieldPath | None = None
    target_version: DocumentSchemaVersionNumber | None = None
    status: DataTaskStatus
    pending_since: Microseconds
    position: DataTaskPosition | None = None
    scanned_count: DocumentCount = DocumentCount(0)
    changed_count: DocumentCount = DocumentCount(0)
    failed_row_count: DocumentCount = DocumentCount(0)
    failed_document_keys: list[StoredDocumentKey] = Field(
        default_factory=list[StoredDocumentKey]
    )
    batch_count: DataTaskBatchCount = DataTaskBatchCount(0)
    started_at: Microseconds | None = None
    last_batch_at: Microseconds | None = None
    finished_at: Microseconds | None = None
    failure_count: DataTaskFailureCount = DataTaskFailureCount(0)
    last_error: DataTaskErrorText | None = None
    release: ReleaseVersion | None = None
