"""
The connections pinned to the running request or job, and small helpers of
the pool's connections (session options, transaction state).

A pin keeps one borrowed connection for a block of code: everything the
same thread does with that pool inside the block runs on it. Session-level
state therefore holds for the whole block (a session advisory lock, an
open unit-of-work transaction), and the block needs one connection however
many statements it runs, so a thread holding a lock never waits for a
second connection that other lock holders keep busy.

The tenant and the platform pool of a process share one registry
(`PinnedConnections`). A pin belongs to the pool that lent its connection,
and the other pool's users reach it only while a transaction is open on it
(a unit of work): work inside a unit joins its transaction whichever pool
it would use on its own, so the unit's writes commit together, on the
unit's role. Outside such a transaction each pool keeps to its own
connections: a read session or a session lock of one pool never carries
the other pool's statements.
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

    def is_lent(self) -> bool:
        """Whether other code uses the pinned connection right now."""
        ...


@dataclass(frozen=True)
class ConnectionPin:
    """A connection pinned by one thread for the pool `owner` (a copied
    context in another thread does not share it: psycopg connections are
    not shared by concurrent statements), and the pin's lender, if any."""

    connection: PostgresConnection
    thread_id: int
    owner: object
    lender: ConnectionLender | None = None

    def holds_open_transaction(self) -> bool:
        """A unit of work's transaction (not a lender's own one) is open on it."""

        is_lender_busy: bool = self.lender is not None and not self.lender.is_lent()
        return not is_lender_busy and not is_idle(self.connection)


class PinnedConnections:
    """
    The pins of the pools of one process, kept per context like the
    storage scope: a stack per thread, the innermost pin last.
    """

    def __init__(self) -> None:
        self._pins: ContextVar[tuple[ConnectionPin, ...]] = ContextVar(
            "postgres_connection_pins",
            default=(),
        )

    def current(self, owner: object) -> PostgresConnection | None:
        """The connection this thread pinned for `owner`, or None outside a pin."""

        pin: ConnectionPin | None = self._own_pin(owner)
        return None if pin is None else pin.connection

    def open_transaction(self) -> PostgresConnection | None:
        """
        The innermost pinned connection of this thread when a unit of
        work's transaction is open on it (whichever pool lent it), else None.
        """

        thread_pins: list[ConnectionPin] = self._pins_of_thread()
        if not thread_pins or not thread_pins[-1].holds_open_transaction():
            return None

        return thread_pins[-1].connection

    @contextmanager
    def lent(
        self, owner: object, joins_open_transaction: bool = True
    ) -> Generator[PostgresConnection | None]:
        """
        For a block of other code: the connection of the open transaction
        of this thread (unless `joins_open_transaction` is off), else the
        connection this thread pinned for `owner` (its lender first ends
        what it keeps open), else None.
        """

        if joins_open_transaction:
            joined: PostgresConnection | None = self.open_transaction()
            if joined is not None:
                yield joined
                return

        pin: ConnectionPin | None = self._own_pin(owner)
        if pin is None or pin.lender is None:
            yield None if pin is None else pin.connection
            return

        with pin.lender.lend():
            yield pin.connection

    @contextmanager
    def pinned(
        self,
        connection: PostgresConnection,
        owner: object,
        lender: ConnectionLender | None = None,
    ) -> Generator[None]:
        pin = ConnectionPin(
            connection=connection,
            thread_id=threading.get_ident(),
            owner=owner,
            lender=lender,
        )
        token: Token[tuple[ConnectionPin, ...]] = self._pins.set(
            (*self._pins.get(), pin)
        )
        try:
            yield
        finally:
            self._pins.reset(token)

    def _own_pin(self, owner: object) -> ConnectionPin | None:
        for pin in reversed(self._pins_of_thread()):
            if pin.owner is owner:
                return pin

        return None

    def _pins_of_thread(self) -> list[ConnectionPin]:
        thread_id: int = threading.get_ident()
        return [pin for pin in self._pins.get() if pin.thread_id == thread_id]


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
