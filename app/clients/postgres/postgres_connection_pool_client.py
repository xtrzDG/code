import threading
import time
from collections.abc import Generator
from contextlib import contextmanager

import psycopg

from app.clients.postgres.pinned_connections import (
    IdleConnection,
    PinnedConnections,
    PostgresConnection,
    build_session_options,
    is_idle,
)
from app.contracts.client_contract import ClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import DatabaseUrl

__all__ = ["PostgresConnection", "PostgresConnectionPoolClient"]

DEFAULT_MAX_POOL_SIZE: int = 10
DEFAULT_ACQUIRE_TIMEOUT_SECONDS: float = 30.0
DEFAULT_CONNECT_TIMEOUT_SECONDS: int = 10
DEFAULT_IDLE_CHECK_SECONDS: float = 30.0
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

    Prepared statements are off by default: transaction poolers in front of
    managed Postgres (PgBouncer, Supavisor) do not support them.

    `statement_timeout_seconds` and `idle_in_transaction_timeout_seconds`
    become the server settings of every connection (startup options), so a
    runaway query or a transaction left open by a stuck thread is ended by
    the server instead of holding locks and a connection for minutes.

    `pinned_connection()` keeps one connection for a block of a thread
    (a session advisory lock, a unit of work): inside it, `connection()`
    and `transaction()` of that thread use the pinned connection, and a
    nested `transaction()` becomes a savepoint.
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
    ) -> None:
        if max_size < 1:
            raise ValueError(
                "A connection pool needs room for at least one connection."
            )

        self._database_url: DatabaseUrl = database_url
        self._max_size: int = max_size
        self._acquire_timeout_seconds: float = acquire_timeout_seconds
        self._connect_timeout_seconds: int = connect_timeout_seconds
        self._idle_check_seconds: float = idle_check_seconds
        self._application_name: str = application_name
        self._prepare_threshold: int | None = (
            5 if is_statement_preparation_enabled else None
        )
        self._session_options: str = build_session_options(
            statement_timeout_seconds, idle_in_transaction_timeout_seconds
        )
        self._condition: threading.Condition = threading.Condition()
        self._idle_connections: list[IdleConnection] = []
        self._open_connection_count: int = 0
        self._is_closed: bool = False
        self._pins: PinnedConnections = PinnedConnections()

    @property
    def max_size(self) -> int:
        return self._max_size

    def open_connection_count(self) -> int:
        """Connections currently open: idle in the pool plus handed out."""

        with self._condition:
            return self._open_connection_count

    def idle_connection_count(self) -> int:
        with self._condition:
            return len(self._idle_connections)

    @contextmanager
    def connection(
        self,
        acquire_timeout_seconds: float | None = None,
    ) -> Generator[PostgresConnection]:
        """
        Borrow one connection (autocommit) for the duration of the block,
        waiting at most `acquire_timeout_seconds` (default: the pool's) for
        a free one. Inside a pin of this thread, the pinned connection.
        """

        pinned_connection: PostgresConnection | None = self._pins.current()
        if pinned_connection is not None:
            yield pinned_connection
            return

        connection: PostgresConnection = self._acquire(
            self._acquire_timeout_seconds
            if acquire_timeout_seconds is None
            else acquire_timeout_seconds
        )
        try:
            yield connection
        finally:
            self._release(connection)

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
    def pinned_connection(self) -> Generator[PostgresConnection]:
        """
        Keep one connection for this thread for the whole block (see the
        class doc); a nested pin reuses the outer one. The connection goes
        back to the pool when the outermost pin ends.
        """

        pinned_connection: PostgresConnection | None = self._pins.current()
        if pinned_connection is not None:
            yield pinned_connection
            return

        with self.connection() as connection, self._pins.pinned(connection):
            yield connection

    def close(self) -> None:
        """Close idle connections now and the borrowed ones when they return."""

        with self._condition:
            self._is_closed = True
            idle_connections: list[IdleConnection] = self._idle_connections
            self._idle_connections = []
            self._open_connection_count -= len(idle_connections)
            self._condition.notify_all()

        for idle_connection in idle_connections:
            idle_connection.connection.close()

    def __del__(self) -> None:
        # Safety net for pools dropped without close(): no open sockets left.
        try:
            self.close()
        except Exception:  # noqa: BLE001 - never raise from a finalizer
            return

    def _acquire(self, timeout_seconds: float) -> PostgresConnection:
        deadline: float = time.monotonic() + timeout_seconds
        while True:
            idle_connection: IdleConnection | None = self._reserve(
                deadline, timeout_seconds
            )
            if idle_connection is None:
                return self._open_new_connection()

            if self._is_usable(idle_connection):
                return idle_connection.connection

            self._discard(idle_connection.connection)

    def _reserve(
        self, deadline: float, timeout_seconds: float
    ) -> IdleConnection | None:
        """Take an idle connection, or reserve a slot for a new one (None)."""

        with self._condition:
            while True:
                if self._is_closed:
                    raise ExternalServiceError(
                        "The database connection pool is closed."
                    )

                if self._idle_connections:
                    return self._idle_connections.pop()

                if self._open_connection_count < self._max_size:
                    self._open_connection_count += 1
                    return None

                remaining_seconds: float = deadline - time.monotonic()
                if remaining_seconds <= 0:
                    raise ExternalServiceError(
                        "No free database connection within "
                        f"{timeout_seconds:g} s "
                        f"(all {self._max_size} are in use)."
                    )

                self._condition.wait(remaining_seconds)

    def _open_new_connection(self) -> PostgresConnection:
        try:
            return psycopg.connect(
                str(self._database_url),
                autocommit=True,
                prepare_threshold=self._prepare_threshold,
                connect_timeout=self._connect_timeout_seconds,
                application_name=self._application_name,
                # None leaves the server's defaults (psycopg drops it).
                options=self._session_options or None,
            )
        except psycopg.Error as error:
            self._forget_slot()
            raise ExternalServiceError(
                f"Could not connect to the database ({type(error).__name__})."
            ) from error
        except BaseException:
            self._forget_slot()
            raise

    def _is_usable(self, idle_connection: IdleConnection) -> bool:
        connection: PostgresConnection = idle_connection.connection
        if connection.closed or connection.broken:
            return False

        idle_seconds: float = time.monotonic() - idle_connection.idle_since
        if idle_seconds < self._idle_check_seconds:
            return True

        try:
            connection.execute("select 1")
        except psycopg.Error:
            return False

        return True

    def _release(self, connection: PostgresConnection) -> None:
        is_reusable: bool = self._reset_for_reuse(connection)
        with self._condition:
            if is_reusable and not self._is_closed:
                self._idle_connections.append(
                    IdleConnection(connection=connection, idle_since=time.monotonic())
                )
                self._condition.notify()
                return

            self._open_connection_count -= 1
            self._condition.notify()

        connection.close()

    def _reset_for_reuse(self, connection: PostgresConnection) -> bool:
        if connection.closed or connection.broken:
            return False

        if is_idle(connection):
            return True

        try:
            connection.rollback()
        except psycopg.Error:
            return False

        return is_idle(connection)

    def _discard(self, connection: PostgresConnection) -> None:
        self._forget_slot()
        connection.close()

    def _forget_slot(self) -> None:
        with self._condition:
            self._open_connection_count -= 1
            self._condition.notify()
