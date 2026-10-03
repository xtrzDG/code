"""
The idle connections of a pool: a stack (the connection returned last is
reused first, so a quiet pool's spare connections age at the bottom) that
gives up the ones unused for too long, down to a floor.
"""

import time
from dataclasses import dataclass

import psycopg

from app.clients.postgres.pinned_connections import PostgresConnection


@dataclass
class IdleConnection:
    """A pooled connection and when it was returned (monotonic seconds)."""

    connection: PostgresConnection
    idle_since: float


class IdleConnections:
    """
    Not thread-safe on its own: the pool calls it under its lock. Reuse
    takes the freshest connection; `take_expired` hands back the oldest ones
    idle for at least `max_idle_seconds` while more than `keep_open`
    connections of the pool are open, for the pool to close outside its lock.
    """

    def __init__(self, max_idle_seconds: float | None) -> None:
        self._max_idle_seconds: float | None = max_idle_seconds
        # Oldest first: connections are pushed when returned.
        self._stack: list[IdleConnection] = []

    def __len__(self) -> int:
        return len(self._stack)

    def push(self, connection: PostgresConnection, now: float) -> None:
        self._stack.append(IdleConnection(connection=connection, idle_since=now))

    def pop_freshest(self) -> IdleConnection | None:
        return self._stack.pop() if self._stack else None

    def take_all(self) -> list[IdleConnection]:
        taken: list[IdleConnection] = self._stack
        self._stack = []
        return taken

    def take_expired(
        self,
        now: float,
        open_count: int,
        keep_open: int,
    ) -> list[PostgresConnection]:
        """The connections to close now (the caller lowers its open count)."""

        if self._max_idle_seconds is None:
            return []

        expired: list[PostgresConnection] = []
        while (
            self._stack
            and open_count - len(expired) > keep_open
            and now - self._stack[0].idle_since >= self._max_idle_seconds
        ):
            expired.append(self._stack.pop(0).connection)

        return expired


def is_usable(idle_connection: IdleConnection, idle_check_seconds: float) -> bool:
    """
    Fit for reuse: open and healthy, and (idle for `idle_check_seconds` or
    more) still answering, since the server may have dropped it meanwhile.
    """

    connection: PostgresConnection = idle_connection.connection
    if connection.closed or connection.broken:
        return False

    idle_seconds: float = time.monotonic() - idle_connection.idle_since
    if idle_seconds < idle_check_seconds:
        return True

    try:
        connection.execute("select 1")
    except psycopg.Error:
        return False

    return True
