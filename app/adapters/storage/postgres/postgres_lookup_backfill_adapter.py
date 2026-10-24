import psycopg
from psycopg import errors
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.lookup_backfill_queries import (
    LOOKUP_COLUMN_PREFIX,
    TRIGGER_COLUMNS_QUERY,
    compose_count_missing,
    compose_fill_batch,
)
from app.adapters.storage.postgres.platform_transaction import platform_transaction
from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
)
from app.adapters.storage.postgres.schema_migration_queries import bound_lock_waits
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.storage import LookupColumnBackfillAdapterContract
from app.schemas.dto.lookup_backfill import LookupBackfillBatch, TriggerLookupColumn
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    LockWaitSeconds,
    LookupBackfillBatchSize,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.schemas.typings.storage.strings import StoredDocumentKey

DEFAULT_LOCK_TIMEOUT: LockWaitSeconds = LockWaitSeconds(5)


class PostgresLookupBackfillAdapter(LookupColumnBackfillAdapterContract):
    """
    Trigger-kept lookup columns on Postgres (`lookup_backfill_queries`).

    Every batch is its own platform-wide transaction (row-level security
    bypassed: the backfill covers every business) that waits at most
    `lock_timeout` for a row another transaction keeps locked, so the live
    application is never queued behind it; a batch that timed out wrote
    nothing and can simply run again.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        lock_timeout: LockWaitSeconds = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._lock_timeout: LockWaitSeconds = lock_timeout

    def list_trigger_columns(self) -> list[TriggerLookupColumn]:
        with platform_transaction(
            self._connection_pool, "lookup columns"
        ) as connection:
            rows: list[TupleRow] = connection.execute(TRIGGER_COLUMNS_QUERY).fetchall()

        return [
            TriggerLookupColumn(
                collection_name=DocumentCollectionName(str(row[0])),
                field=DocumentFieldPath(str(row[1]).removeprefix(LOOKUP_COLUMN_PREFIX)),
            )
            for row in rows
        ]

    def count_missing(self, column: TriggerLookupColumn) -> DocumentCount:
        with platform_transaction(
            self._connection_pool, str(column.collection_name)
        ) as connection:
            row: TupleRow | None = connection.execute(
                compose_count_missing(column)
            ).fetchone()

        return DocumentCount(read_count(row, 0))

    def fill_batch(
        self,
        column: TriggerLookupColumn,
        after: StoredDocumentKey | None,
        batch_size: LookupBackfillBatchSize,
    ) -> LookupBackfillBatch:
        try:
            with self._connection_pool.transaction() as connection:
                apply_storage_scope(connection, StorageScope.platform_wide())
                bound_lock_waits(connection, self._lock_timeout, is_local=True)
                row: TupleRow | None = connection.execute(
                    compose_fill_batch(column),
                    ("" if after is None else str(after), int(batch_size)),
                ).fetchone()
        except (errors.LockNotAvailable, errors.DeadlockDetected) as error:
            raise MigrationLockTimeoutError(
                f"Backfill of {column.collection_name}.{column.field} waited too "
                f"long for a locked row ({type(error).__name__})."
            ) from error
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Backfill of {column.collection_name}.{column.field} failed: "
                f"{type(error).__name__}: {error}"
            ) from error

        if row is None:
            raise ExternalServiceError("The backfill batch returned no summary.")

        last_key: object = row[0]
        return LookupBackfillBatch(
            last_document_key=None
            if last_key is None
            else StoredDocumentKey(str(last_key)),
            scanned_count=DocumentCount(read_count(row, 1)),
            filled_count=DocumentCount(read_count(row, 2)),
        )


def read_count(row: TupleRow | None, column_index: int) -> int:
    value: object = None if row is None else row[column_index]
    if not isinstance(value, int):
        raise ExternalServiceError(
            f"Expected a row count from the database, got {type(value).__name__}."
        )

    return value
