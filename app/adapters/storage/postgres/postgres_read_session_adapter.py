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
from app.contracts.storage import StorageReadSessionContract

READ_SESSION_LABEL: str = "read session"


class PostgresReadSessionAdapter(StorageReadSessionContract):
    """
    A read session on Postgres (`read_sessions`): the block pins one
    connection of the pool, and the document tables run its reads on it in
    one transaction, one statement each, begun at the first read with that
    read's scope in the same round trip; other work of the block borrows
    the connection after the session committed its reads, and runs as it
    would without a session. Nested, or inside another pin of the thread
    (a unit of work, a lock), the block runs as it is.
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool

    @contextmanager
    def read_session(self) -> Generator[None]:
        if (
            self._connection_pool.is_pinned()
            or read_session_of(self._connection_pool) is not None
        ):
            yield
            return

        with (
            storage_errors_translated(READ_SESSION_LABEL),
            entered_read_session(self._connection_pool),
        ):
            yield
