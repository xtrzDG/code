"""
One storage transaction of a pool, with its row-level security scope set
in the round trip that opens it.

Outside a transaction the block is a transaction of its own: `begin` and
the scope's `set_config` go as one message (`begin_in_scope`), and the
block commits when it ends or rolls back when it raises. Inside one (a
unit of work's pinned connection, a read session's lent connection is
outside any) the block is a savepoint of it, opened with its scope the
same way (`savepoint_in_scope`): released when the block ends, rolled
back to (which also restores the scope before it) when it raises. Either
way no statement of the block runs before its scope is set, exactly as
with a `set_config` round trip of its own, one round trip earlier.

A platform-wide read outside a transaction (`scoped_read`) needs neither:
the platform role sees every row whatever `app.business_id` says
(migration 1200), so its statements run on their own, one round trip
each instead of three.

A single read needs no block: `fetch_in_scope` pipelines the scope and the
read on an idle connection (one round trip, one implicit transaction that
ends at the pipeline's sync, so the scope ends with it), and inside a
transaction runs them in a scoped savepoint.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager, suppress
from contextvars import ContextVar, Token
from typing import LiteralString

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
    begin_in_scope,
    savepoint_in_scope,
)
from app.clients.postgres.pinned_connections import is_idle
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.constants.storage import StorageScopeKind
from app.schemas.dto.storage import StorageScope

# One name for every scoped savepoint: they nest strictly, and Postgres
# releases or rolls back to the most recent savepoint of a name.
SCOPED_SAVEPOINT: sql.Identifier = sql.Identifier("workshop_scope")
COMMIT: LiteralString = "commit"
ROLLBACK: LiteralString = "rollback"
RELEASE: sql.Composed = sql.SQL("release savepoint {}").format(SCOPED_SAVEPOINT)
ROLLBACK_TO: sql.Composed = sql.SQL(
    "rollback to savepoint {0}; release savepoint {0}"
).format(SCOPED_SAVEPOINT)

# The scope each open transaction of this context began in, by connection.
_opening_scopes: ContextVar[tuple[tuple[int, StorageScope], ...]] = ContextVar(
    "postgres_transaction_opening_scopes",
    default=(),
)


@contextmanager
def scoped_transaction(
    connection_pool: PostgresConnectionPoolClient, scope: StorageScope
) -> Generator[PostgresConnection]:
    """The block as one transaction (or savepoint) in `scope` (module doc)."""

    with connection_pool.connection() as connection:
        if is_idle(connection):
            begin_in_scope(connection, scope)
            with opened_in(connection, scope), finished(connection, COMMIT, ROLLBACK):
                yield connection
            return

        savepoint_in_scope(
            connection, joined_scope(connection, scope), SCOPED_SAVEPOINT
        )
        with finished(connection, RELEASE, ROLLBACK_TO):
            yield connection


def fetch_in_scope(
    connection_pool: PostgresConnectionPoolClient,
    scope: StorageScope,
    query: LiteralString,
    parameters: Mapping[str, object],
) -> list[TupleRow]:
    """
    The rows of one read in `scope`, in one round trip.

    On an idle connection the scope's `set_config` and the read go as one
    pipeline: the extended protocol runs the statements up to its sync as
    one implicit transaction, so the scope binds the read and ends with it
    (a failure rolls both back). Inside a transaction (a unit of work's
    pinned connection) they run in a savepoint with the scope instead, as
    `scoped_transaction` does.
    """

    with connection_pool.connection() as connection:
        if not is_idle(connection):
            savepoint_in_scope(
                connection, joined_scope(connection, scope), SCOPED_SAVEPOINT
            )
            with finished(connection, RELEASE, ROLLBACK_TO):
                return connection.execute(query, parameters).fetchall()

        with connection.pipeline():
            apply_storage_scope(connection, scope)
            cursor = connection.execute(query, parameters)
        return cursor.fetchall()


@contextmanager
def scoped_read(
    connection_pool: PostgresConnectionPoolClient, scope: StorageScope
) -> Generator[PostgresConnection]:
    """
    One read in `scope`: platform-wide on an idle connection, its
    statements in autocommit (read committed gives each statement its own
    snapshot in a transaction too); otherwise as `scoped_transaction`.
    """

    if scope.kind is StorageScopeKind.PLATFORM:
        with connection_pool.connection() as connection:
            if is_idle(connection):
                yield connection
                return

    # A business's read, or one inside a unit of work's open transaction.
    with scoped_transaction(connection_pool, scope) as connection:
        yield connection


def joined_scope(connection: PostgresConnection, scope: StorageScope) -> StorageScope:
    """
    The scope of a savepoint in `scope` inside the open transaction of
    `connection`: a business scope as it is; another one in the business
    the transaction began for, if it began for one.
    """

    if scope.kind is StorageScopeKind.BUSINESS:
        return scope

    for connection_id, opening_scope in reversed(_opening_scopes.get()):
        if connection_id == id(connection):
            return (
                opening_scope
                if opening_scope.kind is StorageScopeKind.BUSINESS
                else scope
            )

    return scope


@contextmanager
def opened_in(connection: PostgresConnection, scope: StorageScope) -> Generator[None]:
    """Remember the scope the transaction of `connection` began in."""

    token: Token[tuple[tuple[int, StorageScope], ...]] = _opening_scopes.set(
        (*_opening_scopes.get(), (id(connection), scope))
    )
    try:
        yield
    finally:
        _opening_scopes.reset(token)


@contextmanager
def finished(
    connection: PostgresConnection,
    on_success: LiteralString | sql.Composed,
    on_failure: LiteralString | sql.Composed,
) -> Generator[None]:
    """
    Run `on_success` after the block, or `on_failure` when it raises (a
    connection that cannot is broken: the pool discards it, and the
    block's error is the one that counts).
    """

    try:
        yield
    except BaseException:
        with suppress(psycopg.Error):
            connection.execute(on_failure)
        raise

    connection.execute(on_success)
