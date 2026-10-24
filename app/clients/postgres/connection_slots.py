"""
The connections of one pool: opened lazily up to a maximum, reused from
an idle stack, checked after a long idle time, closed after a burst, and
waited for (with a deadline) while every one is in use.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import psycopg

from app.clients.postgres.idle_connections import (
    IdleConnection,
    IdleConnections,
    is_usable,
)
from app.clients.postgres.pinned_connections import (
    PostgresConnection,
    reset_for_reuse,
)
from app.clients.postgres.traced_cursor import TracedCursorClass
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import DatabaseUrl


@dataclass(frozen=True)
class ConnectionOptions:
    """How every connection of a pool is opened (libpq parameters)."""

    database_url: DatabaseUrl
    connect_timeout_seconds: int
    application_name: str
    prepare_threshold: int | None
    session_options: str
    cursor_class: TracedCursorClass | None = None

    def connect(self) -> PostgresConnection:
        return psycopg.connect(
            str(self.database_url),
            autocommit=True,
            prepare_threshold=self.prepare_threshold,
            connect_timeout=self.connect_timeout_seconds,
            application_name=self.application_name,
            # None leaves the server's defaults (psycopg drops it).
            options=self.session_options or None,
            cursor_factory=self.cursor_class,
        )


class ConnectionSlots:
    """
    Thread-safe slots of one pool (`PostgresConnectionPoolClient`), which
    opens connections with `open_connection`: at most `max_size` open;
    idle ones older than `max_idle_seconds` close down to `min_size`; one
    idle for longer than `idle_check_seconds` is pinged before reuse and
    replaced when the server dropped it.
    """

    def __init__(
        self,
        open_connection: Callable[[], PostgresConnection],
        max_size: int,
        min_size: int,
        idle_check_seconds: float,
        max_idle_seconds: float | None,
    ) -> None:
        self._open_connection: Callable[[], PostgresConnection] = open_connection
        self._max_size: int = max_size
        self._min_size: int = min_size
        self._idle_check_seconds: float = idle_check_seconds
        self._condition: threading.Condition = threading.Condition()
        self._idle_connections: IdleConnections = IdleConnections(max_idle_seconds)
        self._open_connection_count: int = 0
        self._is_closed: bool = False

    def open_count(self) -> int:
        with self._condition:
            return self._open_connection_count

    def idle_count(self) -> int:
        with self._condition:
            return len(self._idle_connections)

    def acquire(self, timeout_seconds: float) -> PostgresConnection:
        self._close_expired()
        deadline: float = time.monotonic() + timeout_seconds
        while True:
            idle_connection: IdleConnection | None = self._reserve(
                deadline, timeout_seconds
            )
            if idle_connection is None:
                return self._open_new_connection()

            if is_usable(idle_connection, self._idle_check_seconds):
                return idle_connection.connection

            self._discard(idle_connection.connection)

    def release(self, connection: PostgresConnection) -> None:
        is_reusable: bool = reset_for_reuse(connection)
        with self._condition:
            if is_reusable and not self._is_closed:
                self._idle_connections.push(connection, time.monotonic())
                self._condition.notify()
                return

            self._open_connection_count -= 1
            self._condition.notify()

        connection.close()

    def close(self) -> None:
        """Close idle connections now and the borrowed ones when they return."""

        with self._condition:
            self._is_closed = True
            idle_connections: list[IdleConnection] = self._idle_connections.take_all()
            self._open_connection_count -= len(idle_connections)
            self._condition.notify_all()

        for idle_connection in idle_connections:
            idle_connection.connection.close()

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

                idle_connection: IdleConnection | None = (
                    self._idle_connections.pop_freshest()
                )
                if idle_connection is not None:
                    return idle_connection

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
            return self._open_connection()
        except psycopg.Error as error:
            self._forget_slot()
            raise ExternalServiceError(
                f"Could not connect to the database ({type(error).__name__})."
            ) from error
        except BaseException:
            self._forget_slot()
            raise

    def _close_expired(self) -> None:
        """Close the connections idle past `max_idle_seconds` (down to min_size)."""

        with self._condition:
            expired: list[PostgresConnection] = self._idle_connections.take_expired(
                time.monotonic(), self._open_connection_count, self._min_size
            )
            self._open_connection_count -= len(expired)

        for connection in expired:
            connection.close()

    def _discard(self, connection: PostgresConnection) -> None:
        self._forget_slot()
        connection.close()

    def _forget_slot(self) -> None:
        with self._condition:
            self._open_connection_count -= 1
            self._condition.notify()
