"""Several reads of one storage scope in one transaction: the read session."""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg

from app.adapters.storage.postgres.platform_transaction import (
    storage_errors_translated,
)
from app.adapters.storage.postgres.postgres_session_settings import begin_in_scope
from app.adapters.storage.postgres.read_sessions import (
    entered_read_session,
    read_session_of,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.storage import StorageReadSessionContract, StorageScopeContract
from app.schemas.constants.storage import StorageScopeKind
from app.schemas.dto.storage import StorageScope

READ_SESSION_LABEL: str = "read session"


class PostgresReadSessionAdapter(StorageReadSessionContract):
    """
    A read session on Postgres: the block borrows one connection of the
    pool (not pinned: other pool users of the thread still get their own),
    begins a transaction with the scope of the running code in one round
    trip (`begin_in_scope`) and lets the document tables run their reads
    in that scope on it (`read_sessions`), one statement each; it commits
    when the block ends and rolls back when it raises (it never wrote
    anything). Postgres's default isolation (read committed) gives every
    statement its own snapshot, as when each read was its own transaction.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContract = storage_scope

    @contextmanager
    def read_session(self) -> Generator[None]:
        scope: StorageScope = self._storage_scope.current()
        if (
            scope.kind is StorageScopeKind.UNSCOPED
            or self._connection_pool.is_pinned()
            or read_session_of(self._connection_pool) is not None
        ):
            yield
            return

        with (
            storage_errors_translated(READ_SESSION_LABEL),
            self._connection_pool.connection() as connection,
        ):
            begin_in_scope(connection, scope)
            try:
                with entered_read_session(self._connection_pool, connection, scope):
                    yield
            except BaseException:
                end_quietly(connection)
                raise

            connection.execute("commit")


def end_quietly(connection: PostgresConnection) -> None:
    """
    Roll the session back after an error; a connection that cannot is
    broken, and the pool discards it when it comes back.
    """

    try:
        connection.execute("rollback")
    except psycopg.Error:
        return
