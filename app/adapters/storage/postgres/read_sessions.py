"""
The read session the running code entered (`PostgresReadSessionAdapter`),
for the document tables' reads.

A session is one connection of a pool, in a transaction whose row-level
security scope was set once. It is kept per context like the storage
scope, and serves only the thread that entered it (a thread started with a
copied context does not share the connection) and only reads in the same
scope: anything else borrows a connection of its own, so nothing but the
session's own reads ever runs on its transaction.
"""

import threading
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.dto.storage import StorageScope


@dataclass(frozen=True)
class ReadSession:
    """A connection in an open transaction with `scope` applied."""

    connection_pool: PostgresConnectionPoolClient
    connection: PostgresConnection
    scope: StorageScope
    thread_id: int


_current_read_session: ContextVar[ReadSession | None] = ContextVar(
    "postgres_read_session",
    default=None,
)


def read_session_of(
    connection_pool: PostgresConnectionPoolClient,
) -> ReadSession | None:
    """The session this thread entered on `connection_pool`, if any."""

    session: ReadSession | None = _current_read_session.get()
    if (
        session is None
        or session.connection_pool is not connection_pool
        or session.thread_id != threading.get_ident()
    ):
        return None

    return session


def read_session_connection(
    connection_pool: PostgresConnectionPoolClient,
    scope: StorageScope,
) -> PostgresConnection | None:
    """The connection of this thread's session on the pool for `scope`."""

    session: ReadSession | None = read_session_of(connection_pool)
    if session is None or session.scope != scope:
        return None

    return session.connection


@contextmanager
def entered_read_session(
    connection_pool: PostgresConnectionPoolClient,
    connection: PostgresConnection,
    scope: StorageScope,
) -> Generator[None]:
    token: Token[ReadSession | None] = _current_read_session.set(
        ReadSession(
            connection_pool=connection_pool,
            connection=connection,
            scope=scope,
            thread_id=threading.get_ident(),
        )
    )
    try:
        yield
    finally:
        _current_read_session.reset(token)
