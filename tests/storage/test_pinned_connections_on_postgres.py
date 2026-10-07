"""A pinned connection: one connection for a block of one thread."""

import contextvars
import threading
from collections.abc import Generator

import psycopg
import pytest

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl


def backend_pid(connection_pool: PostgresConnectionPoolClient) -> int:
    with connection_pool.connection() as connection:
        row = connection.execute("select pg_backend_pid()").fetchone()

    assert row is not None
    pid: object = row[0]
    assert isinstance(pid, int)
    return pid


@pytest.fixture
def pool(database_url: DatabaseUrl) -> Generator[PostgresConnectionPoolClient]:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=3)
    try:
        yield connection_pool
    finally:
        connection_pool.close()


def test_everything_in_a_pin_uses_one_connection(
    pool: PostgresConnectionPoolClient,
) -> None:
    with pool.pinned_connection() as pinned:
        pid = backend_pid(pool)
        with pool.transaction() as in_transaction, pool.pinned_connection() as nested:
            assert in_transaction is pinned
            assert nested is pinned
        assert backend_pid(pool) == pid
        assert pool.open_connection_count() == 1

    # Back in the pool, idle and outside any transaction.
    assert pool.idle_connection_count() == 1
    assert backend_pid(pool) == pid


def test_a_transaction_inside_a_pinned_transaction_is_a_savepoint(
    pool: PostgresConnectionPoolClient,
) -> None:
    with pool.pinned_connection() as connection, connection.transaction():
        connection.execute("create temporary table pin_probe (value int)")
        connection.execute("insert into pin_probe values (1)")
        with pytest.raises(psycopg.errors.DivisionByZero), pool.transaction():
            connection.execute("insert into pin_probe values (2)")
            connection.execute("select 1 / 0")
        # The outer transaction goes on without the savepoint's row.
        rows = connection.execute("select value from pin_probe").fetchall()

    assert rows == [(1,)]


def test_another_thread_never_shares_the_pin(
    pool: PostgresConnectionPoolClient,
) -> None:
    pids: list[int] = []

    with pool.pinned_connection():
        pinned_pid = backend_pid(pool)
        # A copied context carries the pin into the thread; it is ignored.
        context = contextvars.copy_context()
        thread = threading.Thread(
            target=lambda: pids.append(context.run(backend_pid, pool))
        )
        thread.start()
        thread.join()

    assert pids != [pinned_pid]
    assert pool.open_connection_count() == 2
