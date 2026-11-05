import logging
import time
from collections.abc import Callable

import psycopg
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.migration_statements import (
    concurrent_index_names,
    drop_invalid_indexes,
    execute_sql,
)
from app.adapters.storage.postgres.schema_migration_queries import (
    DEFAULT_RUNNER_LOCK_WAIT_SECONDS,
    INSERT_QUERY,
    LIST_QUERY,
    MIGRATION_LOCK_KEY,
    bound_lock_waits,
    has_bookkeeping_table,
    is_recorded,
    lock_runners,
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

    Runners are serialized by a session advisory lock, which a waiting
    runner asks for again and again outside any transaction: a runner that
    waited inside a transaction would hold a snapshot that the other
    runner's `CREATE INDEX CONCURRENTLY` waits for (a deadlock). Whoever
    gets the lock re-checks the record first.

    Every statement of a migration waits at most `lock_timeout` for a lock
    (5 s by default): a file that needs a table the live release keeps busy
    fails fast (MigrationLockTimeoutError) instead of queueing every write
    of that table behind it, and the runner tries it again later.

    A transactional file runs in one transaction together with its record
    (simple query protocol, so it may hold many statements and PL/pgSQL
    bodies): a failure leaves nothing behind. A no-transaction file
    (`-- workshop:no-transaction`, for `CREATE INDEX CONCURRENTLY`) runs
    statement by statement and is recorded only after
    its last statement; its statements must be idempotent (`IF NOT EXISTS`,
    `CREATE OR REPLACE`), because a new try runs the file from the start,
    after the indexes a failed try left invalid were dropped.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        lock_timeout: LockWaitSeconds = DEFAULT_LOCK_TIMEOUT,
        sleep: Callable[[float], None] = time.sleep,
        lock_wait_seconds: float = DEFAULT_RUNNER_LOCK_WAIT_SECONDS,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._lock_timeout: LockWaitSeconds = lock_timeout
        self._sleep: Callable[[float], None] = sleep
        self._lock_wait_seconds: float = lock_wait_seconds

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
            with self._connection_pool.connection() as connection:
                lock_runners(connection, self._sleep, self._lock_wait_seconds)
                try:
                    prepare_bookkeeping(connection)
                    if is_recorded(connection, script):
                        return False

                    if script.is_transactional:
                        self._apply_in_transaction(connection, script, applied_at)
                    else:
                        self._apply_statement_by_statement(
                            connection, script, applied_at
                        )
                finally:
                    release_session(connection)
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not record migration {str(script.name)!r} "
                f"({type(error).__name__})."
            ) from error

        return True

    def _apply_in_transaction(
        self,
        connection: PostgresConnection,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> None:
        with connection.transaction():
            bound_lock_waits(connection, self._lock_timeout, is_local=True)
            execute_sql(connection, script, str(script.sql))
            # Session settings a script may have changed end with it.
            connection.execute("reset all")
            self._record(connection, script, applied_at)

    def _apply_statement_by_statement(
        self,
        connection: PostgresConnection,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> None:
        statements: list[SchemaMigrationStatement] = split_sql_statements(
            str(script.sql)
        )
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
    End what a migration set on its session: its settings and the runners'
    lock. A broken connection is discarded by the pool, and the server drops
    a dead session's lock itself.
    """

    try:
        connection.execute("reset all")
        connection.execute("select pg_advisory_unlock(%s)", (MIGRATION_LOCK_KEY,))
    except psycopg.Error:
        logger.warning("Could not release the migration session.", exc_info=True)
