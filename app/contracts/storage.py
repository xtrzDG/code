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
from app.schemas.dto.storage import (
    AppliedSchemaMigration,
    SchemaMigrationScript,
    StorageScope,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId


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
        Run one script and record it in a single transaction.

        Returns False when another runner recorded it first (runners are
        serialized by a database lock). Raises ConflictError when it was
        recorded with a different checksum, ExternalServiceError when the
        script fails (nothing of it is kept).
        """
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
