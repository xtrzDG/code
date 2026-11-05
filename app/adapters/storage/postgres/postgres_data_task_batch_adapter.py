from collections.abc import Mapping, Sequence

import psycopg
from base_pydantic_schemas import PersistentDocument
from psycopg import errors
from psycopg.rows import TupleRow

from app.adapters.storage.document_upgrades import (
    DOCUMENT_UPCASTERS,
    FIRST_SCHEMA_VERSION,
    NO_UPCASTERS,
    DocumentUpcaster,
)
from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.adapters.storage.postgres.document_batch_upgrade_queries import (
    compose_upgrade_window,
    decode_window_position,
    encode_window_position,
)
from app.adapters.storage.postgres.postgres_lookup_backfill_adapter import (
    PostgresLookupBackfillAdapter,
)
from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
)
from app.adapters.storage.postgres.schema_migration_queries import bound_lock_waits
from app.adapters.storage.postgres.stored_document_upgrade_queries import (
    FIRST_POSITION,
    build_stored_document_upgrade_queries,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.data_tasks import DataTaskBatchAdapterContract
from app.schemas.constants.maintenance import DataTaskKind
from app.schemas.constants.storage import StoredDocumentVersionState
from app.schemas.dto.data_tasks import DataTaskBatchRequest, DataTaskBatchResult
from app.schemas.dto.lookup_backfill import LookupBackfillBatch, TriggerLookupColumn
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.maintenance.constrained_strings import DataTaskPosition
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
    LockWaitSeconds,
    LookupBackfillBatchSize,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

DEFAULT_LOCK_TIMEOUT: LockWaitSeconds = LockWaitSeconds(5)
# A batch lists at most this many rows it could not upgrade.
LISTED_FAILURES: int = 20


class PostgresDataTaskBatchAdapter(DataTaskBatchAdapterContract):
    """
    One batch of a post-deploy data task on Postgres, platform-wide.

    A backfill batch is `workshop backfill-lookup`'s (keyset on the
    document key; the trigger fills every lookup column of a rewritten
    row). A migration batch looks at the next rows in `(created_at,
    row_sequence)` order in one transaction whose lock waits are bounded,
    upgrades the outdated ones through the collection's codec and writes
    each back only if it is still what was read, so a concurrent write of
    the application always wins and `updated_at` is kept. Rows of a newer
    version (a rollback in progress) are left alone.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        lock_timeout: LockWaitSeconds = DEFAULT_LOCK_TIMEOUT,
        collections: Sequence[DocumentCollectionDefinition] = DOCUMENT_COLLECTIONS,
        upcasters: Mapping[
            DocumentCollectionName,
            Mapping[DocumentSchemaVersionNumber, DocumentUpcaster],
        ] = DOCUMENT_UPCASTERS,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._lock_timeout: LockWaitSeconds = lock_timeout
        self._lookups: PostgresLookupBackfillAdapter = PostgresLookupBackfillAdapter(
            connection_pool, lock_timeout
        )
        self._codecs: dict[
            DocumentCollectionName, PersistedDocumentCodec[PersistentDocument]
        ] = {
            definition.name: PersistedDocumentCodec(
                definition.document_type,
                definition.name,
                upcasters.get(definition.name, NO_UPCASTERS),
            )
            for definition in collections
        }

    def run_batch(self, request: DataTaskBatchRequest) -> DataTaskBatchResult:
        if request.task.kind is DataTaskKind.BACKFILL_LOOKUP:
            return self._fill(request)

        return self._upgrade(request)

    def _fill(self, request: DataTaskBatchRequest) -> DataTaskBatchResult:
        field = request.task.field
        if field is None:
            raise NotFoundError(f"The backfill {request.task.key} names no field.")

        batch: LookupBackfillBatch = self._lookups.fill_batch(
            TriggerLookupColumn(
                collection_name=request.task.collection_name, field=field
            ),
            None if request.after is None else StoredDocumentKey(str(request.after)),
            LookupBackfillBatchSize(int(request.batch_size)),
        )
        is_last: bool = batch.last_document_key is None or int(
            batch.scanned_count
        ) < int(request.batch_size)
        return DataTaskBatchResult(
            next_position=None
            if is_last or batch.last_document_key is None
            else DataTaskPosition(str(batch.last_document_key)),
            scanned=batch.scanned_count,
            changed=batch.filled_count,
        )

    def _upgrade(self, request: DataTaskBatchRequest) -> DataTaskBatchResult:
        collection_name: DocumentCollectionName = request.task.collection_name
        codec = self._codecs.get(collection_name)
        if codec is None:
            raise NotFoundError(f"{collection_name!s} is not a document collection.")

        version: DocumentSchemaVersionNumber = codec.current_version or (
            FIRST_SCHEMA_VERSION
        )
        after: tuple[int, int] = (
            FIRST_POSITION
            if request.after is None
            else decode_window_position(request.after)
        )
        try:
            with self._connection_pool.transaction() as connection:
                apply_storage_scope(connection, StorageScope.platform_wide())
                bound_lock_waits(connection, self._lock_timeout, is_local=True)
                rows: list[TupleRow] = connection.execute(
                    compose_upgrade_window(collection_name),
                    {
                        "after_created_at": after[0],
                        "after_row_sequence": after[1],
                        "current_version": str(int(version)),
                        "batch_size": int(request.batch_size),
                    },
                ).fetchall()
                changed, failed = self._rewrite(
                    connection, collection_name, codec, rows
                )
        except (errors.LockNotAvailable, errors.DeadlockDetected) as error:
            raise MigrationLockTimeoutError(
                f"Migration of {collection_name!s} waited too long for a locked "
                f"row ({type(error).__name__})."
            ) from error
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Migration of {collection_name!s} failed: "
                f"{type(error).__name__}: {error}"
            ) from error

        is_last: bool = len(rows) < int(request.batch_size)
        return DataTaskBatchResult(
            next_position=None if is_last else last_window_position(rows),
            scanned=DocumentCount(len(rows)),
            changed=DocumentCount(changed),
            failed_document_keys=[StoredDocumentKey(key) for key in failed],
        )

    def _rewrite(
        self,
        connection: PostgresConnection,
        collection_name: DocumentCollectionName,
        codec: PersistedDocumentCodec[PersistentDocument],
        rows: list[TupleRow],
    ) -> tuple[int, list[str]]:
        """Rows rewritten, and the keys of those that could not be upgraded."""

        rewrite = build_stored_document_upgrade_queries(collection_name).rewrite
        changed: int = 0
        failed: list[str] = []
        for row in rows:
            stored_text: object = row[1]
            if not isinstance(stored_text, str):
                continue

            try:
                if codec.version_state(stored_text) is not (
                    StoredDocumentVersionState.OLDER
                ):
                    continue

                upgraded_text: str = codec.upgrade(stored_text)
            except ValueError, KeyError, TypeError:
                # Unreadable JSON, a document its upcasters cannot make valid
                # (pydantic's ValidationError is a ValueError), an upcaster
                # that does not fit the data.
                if len(failed) < LISTED_FAILURES:
                    failed.append(str(row[0]))
                continue

            changed += connection.execute(
                rewrite,
                {
                    "upgraded": upgraded_text,
                    "document_key": str(row[0]),
                    "stored": stored_text,
                },
            ).rowcount

        return changed, failed


def last_window_position(rows: list[TupleRow]) -> DataTaskPosition:
    created_at: object = rows[-1][2]
    row_sequence: object = rows[-1][3]
    if not isinstance(created_at, int) or not isinstance(row_sequence, int):
        raise ExternalServiceError("created_at and row_sequence must be integers.")

    return encode_window_position(created_at, row_sequence)
