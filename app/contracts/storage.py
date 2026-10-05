"""Storage seams beyond document collections: tenant scope and migrations
(of the SQL schema and of stored documents)."""

from contextlib import AbstractContextManager
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.document_upgrades import (
    CollectionUpgradeReport,
    CollectionUpgradeRequest,
)
from app.schemas.dto.lookup_backfill import LookupBackfillBatch, TriggerLookupColumn
from app.schemas.dto.storage import (
    AppliedSchemaMigration,
    SchemaMigrationScript,
    StorageScope,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    LookupBackfillBatchSize,
    MigrationAttemptNumber,
)
from app.schemas.typings.storage.strings import StoredDocumentKey


class StorageScopeContract(UtilityContract, Protocol):
    """
    Ambient storage scope of the current request, job or thread.

    The document collections read it on every operation of a tenant
    collection, and on Postgres row-level security enforces it, as a second
    line of defence after repositories that already filter by business id.
    It is fail-closed: code that entered no scope is UNSCOPED, and tenant
    collections refuse it (`UnscopedStorageAccessError`); platform-level
    code says so with `platform_wide()`.
    """

    def current(self) -> StorageScope:
        """The scope of the running code; UNSCOPED when it entered none."""
        raise NotImplementedError

    def scoped_to_business(
        self,
        business_id: BusinessId,
    ) -> AbstractContextManager[StorageScope]:
        """Run the block so that tenant collections see only this business."""
        raise NotImplementedError

    def platform_wide(self) -> AbstractContextManager[StorageScope]:
        """Run the block with platform-wide access (explicit escalation)."""
        raise NotImplementedError


class StorageUnitOfWorkContract(AdapterContract, Protocol):
    def unit_of_work(self) -> AbstractContextManager[None]:
        """
        Run the block as one storage transaction on one connection, in the
        current storage scope: its writes commit together when the block
        ends, or none of them when it raises. A unit inside a unit is a
        savepoint of the outer one.
        """
        raise NotImplementedError


class SchemaMigrationSourceAdapterContract(AdapterContract, Protocol):
    def load_scripts(self) -> list[SchemaMigrationScript]:
        """
        All migration scripts, ordered by version.

        Raises ValidationFailedError for misnamed files and duplicate versions.
        """
        raise NotImplementedError


class SchemaMigrationStoreAdapterContract(AdapterContract, Protocol):
    def list_applied(self) -> list[AppliedSchemaMigration]:
        """Migrations recorded in the database, ordered by name."""
        raise NotImplementedError

    def apply_if_pending(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
        """
        Run one script and record it: a transactional script together with
        its record in one transaction; a no-transaction script statement by
        statement, recorded only after the last one succeeded.

        Every lock a script waits for is bounded by the store's lock
        timeout. Returns False when another runner recorded it first
        (runners are serialized by a database lock). Raises ConflictError
        when it was recorded with a different checksum,
        MigrationLockTimeoutError when a lock was not granted in time (the
        try left nothing behind that a new try would not redo), and
        ExternalServiceError when the script fails.
        """
        raise NotImplementedError


class MigrationRetryPauseContract(UtilityContract, Protocol):
    """How long the migration runner waits before it tries a file again."""

    def pause(self, attempt: MigrationAttemptNumber) -> None:
        """Wait before the try after `attempt` (a growing, jittered pause)."""
        raise NotImplementedError


class StoredDocumentUpgradeAdapterContract(AdapterContract, Protocol):
    def upgrade_collection(
        self,
        request: CollectionUpgradeRequest,
    ) -> CollectionUpgradeReport:
        """
        Rewrite the collection's documents of an older schema version in the
        current version's shape, platform-wide (all businesses), in
        transactions of `batch_size` rows; a dry run writes nothing.

        Idempotent: a row is written only if it is still what was read, and
        current rows are never touched, so a second run upgrades nothing.
        Rows of a newer version are counted and left alone; a row that
        cannot be upgraded is counted as failed and the run goes on.
        NotFoundError for a collection outside the catalog.
        """
        raise NotImplementedError


class LookupColumnBackfillAdapterContract(AdapterContract, Protocol):
    """
    The trigger-kept lookup columns of the database and their backfill,
    platform-wide (row-level security bypassed): rows written before a
    column's migration get its value in keyset batches, each its own short
    transaction whose lock waits are bounded.
    """

    def list_trigger_columns(self) -> list[TriggerLookupColumn]:
        """Every trigger-kept `doc_<field>` column, by table and column."""
        raise NotImplementedError

    def count_missing(self, column: TriggerLookupColumn) -> DocumentCount:
        """Rows whose document has the field but whose column is empty."""
        raise NotImplementedError

    def fill_batch(
        self,
        column: TriggerLookupColumn,
        after: StoredDocumentKey | None,
        batch_size: LookupBackfillBatchSize,
    ) -> LookupBackfillBatch:
        """
        Look at the next `batch_size` rows after the key `after` (primary
        key order) and fill the column where it is still empty.

        Raises:
            MigrationLockTimeoutError: a row stayed locked by another
                transaction for longer than the lock timeout (nothing of
                the batch was written).
        """
        raise NotImplementedError
