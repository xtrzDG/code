import logging

import psycopg
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.migration_statements import (
    concurrent_index_names,
    drop_invalid_indexes,
    execute_sql,
)
from app.adapters.storage.postgres.schema_migration_queries import (
    INSERT_QUERY,
    LIST_QUERY,
    MIGRATION_LOCK_KEY,
    bound_lock_waits,
    has_bookkeeping_table,
    is_recorded,
    prepare_bookkeeping,
    read_integer,
    read_text,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.storage import SchemaMigrationStoreAdapterContract
from app.schemas.dto.storage import AppliedSchemaMigration, SchemaMigrationScript
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)
from app.schemas.typings.storage.strings import SchemaMigrationStatement
from app.utilities.storage.sql_statements import split_sql_statements

DEFAULT_LOCK_TIMEOUT: LockWaitSeconds = LockWaitSeconds(5)
logger: logging.Logger = logging.getLogger(__name__)


class PostgresSchemaMigrationStoreAdapter(SchemaMigrationStoreAdapterContract):
    """
    Records applied migrations in `workshop.schema_migrations`.

    Runners are serialized by an advisory lock; whoever gets it re-checks
    the record first. Every statement of a migration waits at most
    `lock_timeout` for a lock (5 s by default): a file that needs a table
    the live release keeps busy fails fast (MigrationLockTimeoutError)
    instead of queueing every write of that table behind it, and the
    runner tries it again later.

    A transactional file runs in one transaction together with its record
    (simple query protocol, so it may hold many statements and PL/pgSQL
    bodies): a failure leaves nothing behind. A no-transaction file
    (`-- workshop:no-transaction`, for `CREATE INDEX CONCURRENTLY`) runs
    statement by statement under a session lock and is recorded only after
    its last statement; its statements must be idempotent (`IF NOT EXISTS`,
    `CREATE OR REPLACE`), because a new try runs the file from the start,
    after the indexes a failed try left invalid were dropped.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        lock_timeout: LockWaitSeconds = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._lock_timeout: LockWaitSeconds = lock_timeout

    def list_applied(self) -> list[AppliedSchemaMigration]:
        try:
            with self._connection_pool.transaction() as connection:
                if not has_bookkeeping_table(connection):
                    return []

                rows: list[TupleRow] = connection.execute(LIST_QUERY).fetchall()
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not read applied migrations ({type(error).__name__})."
            ) from error

        return [
            AppliedSchemaMigration(
                name=SchemaMigrationName(read_text(row, 0)),
                checksum=SchemaMigrationChecksum(read_text(row, 1)),
                applied_at=Microseconds(read_integer(row, 2)),
            )
            for row in rows
        ]

    def apply_if_pending(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
        try:
            if script.is_transactional:
                return self._apply_in_transaction(script, applied_at)

            return self._apply_statement_by_statement(script, applied_at)
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not record migration {str(script.name)!r} "
                f"({type(error).__name__})."
            ) from error

    def _apply_in_transaction(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
        with self._connection_pool.transaction() as connection:
            # Waiting for another runner is fine; only the file's own locks
            # are bounded, so the timeout starts after this lock.
            connection.execute(
                "select pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,)
            )
            prepare_bookkeeping(connection)
            if is_recorded(connection, script):
                return False

            bound_lock_waits(connection, self._lock_timeout, is_local=True)
            execute_sql(connection, script, str(script.sql))
            # Session settings a script may have changed end with it.
            connection.execute("reset all")
            self._record(connection, script, applied_at)

        return True

    def _apply_statement_by_statement(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
        statements: list[SchemaMigrationStatement] = split_sql_statements(
            str(script.sql)
        )
        with self._connection_pool.connection() as connection:
            connection.execute("select pg_advisory_lock(%s)", (MIGRATION_LOCK_KEY,))
            try:
                prepare_bookkeeping(connection)
                if is_recorded(connection, script):
                    return False

                bound_lock_waits(connection, self._lock_timeout, is_local=False)
                dropped: list[str] = drop_invalid_indexes(
                    connection, script, concurrent_index_names(statements)
                )
                if dropped:
                    logger.warning(
                        "Migration %s: rebuilding invalid indexes %s.",
                        script.name,
                        ", ".join(dropped),
                    )
                for statement in statements:
                    execute_sql(connection, script, str(statement))
                self._record(connection, script, applied_at)
            finally:
                release_session(connection)

        return True

    def _record(
        self,
        connection: PostgresConnection,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> None:
        connection.execute(
            INSERT_QUERY, (str(script.name), str(script.checksum), int(applied_at))
        )


def release_session(connection: PostgresConnection) -> None:
    """
    End what a no-transaction file set on its session: its settings and the
    runners' lock. A broken connection is discarded by the pool, and the
    server drops a dead session's lock itself.
    """

    try:
        connection.execute("reset all")
        connection.execute("select pg_advisory_unlock(%s)", (MIGRATION_LOCK_KEY,))
    except psycopg.Error:
        logger.warning("Could not release the migration session.", exc_info=True)
