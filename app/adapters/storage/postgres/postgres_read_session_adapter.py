"""Several reads in one transaction on one connection: the read session."""

from collections.abc import Generator
from contextlib import contextmanager

from app.adapters.storage.postgres.platform_transaction import (
    storage_errors_translated,
)
from app.adapters.storage.postgres.read_sessions import (
    entered_read_session,
    read_session_of,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.storage import StorageReadSessionContract, StorageScopeContract

READ_SESSION_LABEL: str = "read session"


class PostgresReadSessionAdapter(StorageReadSessionContract):
    """
    A read session on Postgres (`read_sessions`): the block pins one
    connection of the pool of the running code's scope (the tenant pool for
    a business, the platform pool otherwise), and the document tables that
    read in that scope run their reads on it in
    one transaction, one statement each, begun at the first read with that
    read's scope in the same round trip; other work of the block borrows
    the connection after the session committed its reads, and runs as it
    would without a session (reads of the other pool's scope too). Nested,
    or inside another pin of the thread (a unit of work, a lock), the block
    runs as it is.
    """

    def __init__(
        self,
        connection_pools: PostgresConnectionPools,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._connection_pools: PostgresConnectionPools = connection_pools
        self._storage_scope: StorageScopeContract = storage_scope

    @contextmanager
    def read_session(self) -> Generator[None]:
        connection_pool: PostgresConnectionPoolClient = (
            self._connection_pools.for_scope(self._storage_scope.current())
        )
        if (
            self._connection_pools.is_pinned()
            or read_session_of(connection_pool) is not None
        ):
            yield
            return

        with (
            storage_errors_translated(READ_SESSION_LABEL),
            entered_read_session(connection_pool),
        ):
            yield
