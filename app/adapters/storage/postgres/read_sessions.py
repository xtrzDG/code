"""
The read session the running code entered (`PostgresReadSessionAdapter`),
for the document tables' reads.

A session pins one connection of a pool for the thread that entered it (a
thread started with a copied context does not share it) and lets the
thread's reads share one transaction on it: the transaction begins at the
first read, with that read's storage scope in the same round trip
(`begin_in_scope`), and a read in another scope sets its scope for the
rest of the transaction first (row-level security sees the scope of each
read, as when every read was a transaction of its own). Postgres's default
isolation (read committed) gives every statement its own snapshot, so a
read sees what was committed when it runs, as outside a session.

Anything else that uses the pool on the thread meanwhile (a write, a unit
of work, a lock, a platform statement) borrows the pinned connection: the
session commits its read transaction before handing the connection over
(`lend`), so that work runs in transactions of its own and commits as it
would without a session, on the same connection (a session never holds a
second connection of the pool); the next read begins a new transaction.
Reads made while the connection is lent run as they would without a
session (inside a unit of work: as its savepoints). A read that fails
rolls the session's transaction back; the next read begins a new one.
"""

import threading
from collections.abc import Generator
from contextlib import contextmanager, suppress
from contextvars import ContextVar, Token

import psycopg

from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
    begin_in_scope,
)
from app.clients.postgres.pinned_connections import ConnectionLender
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.dto.storage import StorageScope


class ReadSession(ConnectionLender):
    """
    The reads of one thread on one pinned connection of a pool, in a
    transaction begun lazily (`scope` is its storage scope, None while no
    transaction is open).
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self.connection_pool: PostgresConnectionPoolClient = connection_pool
        self.thread_id: int = threading.get_ident()
        self.scope: StorageScope | None = None
        self._connection: PostgresConnection | None = None
        self._lent_count: int = 0

    @property
    def connection(self) -> PostgresConnection:
        if self._connection is None:
            raise RuntimeError("The read session has no connection yet.")

        return self._connection

    def attach(self, connection: PostgresConnection) -> None:
        self._connection = connection

    def is_lent(self) -> bool:
        return self._lent_count > 0

    def connection_in(self, scope: StorageScope) -> PostgresConnection | None:
        """
        The connection with a read transaction open in `scope` (begun or
        rescoped now), or None while it is lent to other code.
        """

        if self.is_lent():
            return None

        try:
            if self.scope is None:
                begin_in_scope(self.connection, scope)
            elif self.scope != scope:
                apply_storage_scope(self.connection, scope)
        except psycopg.Error:
            self.scope = scope
            self.abandon()
            raise

        self.scope = scope
        return self.connection

    @contextmanager
    def lend(self) -> Generator[None]:
        self.end()
        self._lent_count += 1
        try:
            yield
        finally:
            self._lent_count -= 1

    def end(self) -> None:
        """Commit the open read transaction, if any."""

        if self.scope is None:
            return

        self.scope = None
        self.connection.execute("commit")

    def abandon(self) -> None:
        """
        Roll the open read transaction back (after a failed read); a
        connection that cannot is broken, and the pool discards it.
        """

        if self.scope is None:
            return

        self.scope = None
        with suppress(psycopg.Error):
            self.connection.execute("rollback")


_current_read_session: ContextVar[ReadSession | None] = ContextVar(
    "postgres_read_session",
    default=None,
)


def read_session_of(
    connection_pool: PostgresConnectionPoolClient,
) -> ReadSession | None:
    """
    The session this thread entered on `connection_pool`, or on the pool
    that serves every pool (a platform session also carries the reads of
    a business's scope inside it), if any.
    """

    session: ReadSession | None = _current_read_session.get()
    if (
        session is None
        or session.thread_id != threading.get_ident()
        or not (
            session.connection_pool is connection_pool
            or session.connection_pool.serves_every_pool()
        )
    ):
        return None

    return session


@contextmanager
def read_session_connection(
    connection_pool: PostgresConnectionPoolClient,
    scope: StorageScope,
) -> Generator[PostgresConnection | None]:
    """
    For one read: this thread's session connection on the pool, in a read
    transaction of `scope` (None without a session or while it is lent).
    A database error of the read rolls the session's transaction back.
    """

    session: ReadSession | None = read_session_of(connection_pool)
    connection: PostgresConnection | None = (
        None if session is None else session.connection_in(scope)
    )
    if session is None or connection is None:
        yield None
        return

    try:
        yield connection
    except psycopg.Error:
        session.abandon()
        raise


@contextmanager
def entered_read_session(
    connection_pool: PostgresConnectionPoolClient,
) -> Generator[ReadSession]:
    """
    Pin a connection of the pool for a session of this thread; the open
    read transaction commits when the block ends and rolls back when it
    raises (it never wrote anything).
    """

    session = ReadSession(connection_pool)
    with connection_pool.pinned_connection(lender=session) as connection:
        session.attach(connection)
        token: Token[ReadSession | None] = _current_read_session.set(session)
        try:
            yield session
        except BaseException:
            session.abandon()
            raise
        finally:
            _current_read_session.reset(token)

        session.end()
