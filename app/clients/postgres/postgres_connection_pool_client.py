import time
from collections.abc import Generator
from contextlib import contextmanager

from app.clients.postgres.connection_slots import ConnectionOptions, ConnectionSlots
from app.clients.postgres.pinned_connections import (
    ConnectionLender,
    PinnedConnections,
    PostgresConnection,
    build_session_options,
)
from app.clients.postgres.pool_instruments import NO_POOL_INSTRUMENTS, PoolInstruments
from app.contracts.client_contract import ClientContract
from app.schemas.typings.platform.strings import DatabaseUrl

__all__ = ["PostgresConnection", "PostgresConnectionPoolClient"]

DEFAULT_MAX_POOL_SIZE: int = 10
DEFAULT_ACQUIRE_TIMEOUT_SECONDS: float = 30.0
DEFAULT_CONNECT_TIMEOUT_SECONDS: int = 10
DEFAULT_IDLE_CHECK_SECONDS: float = 30.0
DEFAULT_MIN_POOL_SIZE: int = 0
DEFAULT_APPLICATION_NAME: str = "assistant-workshop"


class PostgresConnectionPoolClient(ClientContract):
    """
    Small thread-safe pool of synchronous psycopg connections.

    Connections open lazily up to `max_size`; callers wait up to
    `acquire_timeout_seconds` for a free one. Connections run in autocommit
    mode, so every `transaction()` is an explicit BEGIN/COMMIT and nothing
    (including SET LOCAL settings) leaks between users. A connection that
    comes back broken, closed, or stuck in a transaction it cannot roll back
    is discarded; one idle for longer than `idle_check_seconds` is pinged
    before reuse and replaced when the server dropped it (restart, idle
    timeout), so a stale connection rarely fails a request.

    The pool shrinks after a burst: whenever it is used, connections idle
    for `max_idle_seconds` are closed while more than `min_size` are open,
    so a deploy's overlap fits the server's connection limit. Prepared
    statements are off by default: transaction poolers in front of managed
    Postgres (PgBouncer, Supavisor) do not support them.

    `statement_timeout_seconds` and `idle_in_transaction_timeout_seconds`
    become server settings of every connection (startup options): the
    server ends a runaway query or a transaction a stuck thread left open.

    `pinned_connection()` keeps one connection for a block of a thread
    (a session advisory lock, a unit of work, a read session): inside it,
    `connection()` and `transaction()` of that thread use the pinned
    connection (a nested `transaction()` is a savepoint). Pools that share
    `pins` (a process's tenant and platform pools, `PostgresConnectionPools`)
    also join each other's open unit-of-work transaction
    (`pinned_connections`). `instruments` measure waits and connections in
    use, and trace statements.
    """

    def __init__(
        self,
        database_url: DatabaseUrl,
        max_size: int = DEFAULT_MAX_POOL_SIZE,
        acquire_timeout_seconds: float = DEFAULT_ACQUIRE_TIMEOUT_SECONDS,
        connect_timeout_seconds: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        idle_check_seconds: float = DEFAULT_IDLE_CHECK_SECONDS,
        application_name: str = DEFAULT_APPLICATION_NAME,
        is_statement_preparation_enabled: bool = False,
        statement_timeout_seconds: int | None = None,
        idle_in_transaction_timeout_seconds: int | None = None,
        min_size: int = DEFAULT_MIN_POOL_SIZE,
        max_idle_seconds: float | None = None,
        instruments: PoolInstruments = NO_POOL_INSTRUMENTS,
        pins: PinnedConnections | None = None,
    ) -> None:
        if max_size < 1:
            raise ValueError("A pool needs room for at least one connection.")

        self._max_size: int = max_size
        self._acquire_timeout_seconds: float = acquire_timeout_seconds
        self._connection_options: ConnectionOptions = ConnectionOptions(
            database_url=database_url,
            connect_timeout_seconds=connect_timeout_seconds,
            application_name=application_name,
            prepare_threshold=5 if is_statement_preparation_enabled else None,
            session_options=build_session_options(
                statement_timeout_seconds, idle_in_transaction_timeout_seconds
            ),
            cursor_class=instruments.cursor_class,
        )
        self._slots: ConnectionSlots = ConnectionSlots(
            self._open_new_connection,
            max_size=max_size,
            # A floor above the ceiling would only keep every connection.
            min_size=max(0, min(min_size, max_size)),
            idle_check_seconds=idle_check_seconds,
            max_idle_seconds=max_idle_seconds,
        )
        self._pins: PinnedConnections = PinnedConnections() if pins is None else pins
        self._instruments: PoolInstruments = instruments

    @property
    def max_size(self) -> int:
        return self._max_size

    def is_pinned(self) -> bool:
        """
        Whether this thread runs inside a `pinned_connection()` block of this
        pool, or inside an open unit of work it would join.
        """

        return (
            self._pins.current(self) is not None
            or self._pins.open_transaction() is not None
        )

    def open_connection_count(self) -> int:
        """Connections currently open: idle in the pool plus handed out."""

        return self._slots.open_count()

    def idle_connection_count(self) -> int:
        return self._slots.idle_count()

    @contextmanager
    def connection(
        self,
        acquire_timeout_seconds: float | None = None,
        joins_open_transaction: bool = True,
    ) -> Generator[PostgresConnection]:
        """
        Borrow one connection (autocommit) for the block, waiting at most
        `acquire_timeout_seconds` (default: the pool's) for a free one.
        Inside an open unit of work of this thread, its connection (unless
        `joins_open_transaction` is off); inside a pin of this pool, the
        pinned connection.
        """

        with self._pins.lent(self, joins_open_transaction) as pinned_connection:
            if pinned_connection is not None:
                yield pinned_connection
                return

        started: float = time.monotonic()
        connection: PostgresConnection = self._slots.acquire(
            self._acquire_timeout_seconds
            if acquire_timeout_seconds is None
            else acquire_timeout_seconds
        )
        self._instruments.connection_taken(time.monotonic() - started)
        try:
            yield connection
        finally:
            self._slots.release(connection)
            self._instruments.connection_returned()

    @contextmanager
    def transaction(self) -> Generator[PostgresConnection]:
        """
        Borrow a connection inside one transaction; an error rolls it back.
        Inside a pin whose connection is already in a transaction, a
        savepoint of it (its error rolls back only the savepoint).
        """

        with self.connection() as connection, connection.transaction():
            yield connection

    @contextmanager
    def pinned_connection(
        self, lender: ConnectionLender | None = None
    ) -> Generator[PostgresConnection]:
        """
        Keep one connection for this thread for the whole block (see the
        class doc) until the outermost pin ends; a nested pin reuses it, and
        a pin inside an open unit of work of the thread is that unit's
        connection. The `lender` of the outermost pin hands it to the
        thread's other users of the pool (`ConnectionLender`).
        """

        with self._pins.lent(self) as pinned_connection:
            if pinned_connection is not None:
                yield pinned_connection
                return

        with (
            self.connection() as connection,
            self._pins.pinned(connection, self, lender),
        ):
            yield connection

    def close(self) -> None:
        """Close idle connections now and the borrowed ones when they return."""

        self._slots.close()

    def _open_new_connection(self) -> PostgresConnection:
        """A new connection of this pool (libpq parameters of the pool)."""

        return self._connection_options.connect()

    def __del__(self) -> None:  # pools dropped without close(): no sockets left
        try:
            self.close()
        except Exception:  # noqa: BLE001 - never raise from a finalizer
            return
