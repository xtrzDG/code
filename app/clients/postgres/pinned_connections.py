"""
The connection pinned to the running request or job, and small helpers of
the pool's connections (session options, transaction state).

A pin keeps one borrowed connection for a block of code: everything the
same thread does with the pool inside the block runs on it. Session-level
state therefore holds for the whole block (a session advisory lock, an
open unit-of-work transaction), and the block needs one connection however
many statements it runs, so a thread holding a lock never waits for a
second connection that other lock holders keep busy.
"""

import threading
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg import pq
from psycopg.rows import TupleRow

type PostgresConnection = psycopg.Connection[TupleRow]


class ConnectionLender(Protocol):
    """
    The owner of a pin that keeps something open on its connection between
    its own statements (a read session's transaction): before any other
    code of the thread uses the pinned connection, `lend` ends it, so that
    code finds the connection as a freshly borrowed one.
    """

    def lend(self) -> AbstractContextManager[None]:
        """The block in which other code uses the pinned connection."""
        ...


@dataclass(frozen=True)
class ConnectionPin:
    """A connection pinned by one thread (a copied context in another
    thread does not share it: psycopg connections are not shared by
    concurrent statements), and the pin's lender, if any."""

    connection: PostgresConnection
    thread_id: int
    lender: ConnectionLender | None = None


class PinnedConnections:
    """The pins of one pool, kept per context like the storage scope."""

    def __init__(self) -> None:
        self._current_pin: ContextVar[ConnectionPin | None] = ContextVar(
            "postgres_connection_pin",
            default=None,
        )

    def current(self) -> PostgresConnection | None:
        """The connection this thread pinned, or None outside a pin."""

        pin: ConnectionPin | None = self._pin_of_thread()
        return None if pin is None else pin.connection

    @contextmanager
    def lent(self) -> Generator[PostgresConnection | None]:
        """
        The connection this thread pinned, for a block of other code (None
        outside a pin): the pin's lender first ends what it keeps open.
        """

        pin: ConnectionPin | None = self._pin_of_thread()
        if pin is None or pin.lender is None:
            yield None if pin is None else pin.connection
            return

        with pin.lender.lend():
            yield pin.connection

    @contextmanager
    def pinned(
        self, connection: PostgresConnection, lender: ConnectionLender | None = None
    ) -> Generator[None]:
        token: Token[ConnectionPin | None] = self._current_pin.set(
            ConnectionPin(
                connection=connection,
                thread_id=threading.get_ident(),
                lender=lender,
            )
        )
        try:
            yield
        finally:
            self._current_pin.reset(token)

    def _pin_of_thread(self) -> ConnectionPin | None:
        pin: ConnectionPin | None = self._current_pin.get()
        if pin is None or pin.thread_id != threading.get_ident():
            return None

        return pin


def build_session_options(
    statement_timeout_seconds: int | None,
    idle_in_transaction_timeout_seconds: int | None,
) -> str:
    """libpq `options` that set the server's timeouts for one connection."""

    settings: list[str] = []
    if statement_timeout_seconds is not None:
        settings.append(f"-c statement_timeout={int(statement_timeout_seconds)}s")
    if idle_in_transaction_timeout_seconds is not None:
        settings.append(
            "-c idle_in_transaction_session_timeout="
            f"{int(idle_in_transaction_timeout_seconds)}s"
        )

    return " ".join(settings)


def is_idle(connection: PostgresConnection) -> bool:
    """True when the connection is outside any transaction."""

    return connection.info.transaction_status is pq.TransactionStatus.IDLE


def reset_for_reuse(connection: PostgresConnection) -> bool:
    """
    Bring a returned connection back outside any transaction; False when it
    cannot go back to the pool (closed, broken, or the rollback failed).
    """

    if connection.closed or connection.broken:
        return False

    if is_idle(connection):
        return True

    try:
        connection.rollback()
    except psycopg.Error:
        return False

    return is_idle(connection)
