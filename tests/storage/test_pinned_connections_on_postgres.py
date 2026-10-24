"""
A pinned connection: one connection for a block of one thread. With the two
roles' pools (migration 1200) a platform pin serves the tenant pool's work
too, so it never waits for a tenant connection; a tenant pin borrows a
platform connection for platform work.
"""

import contextvars
import threading
from collections.abc import Generator

import psycopg
import pytest

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from tests.storage.postgres_roles import (
    PLATFORM_LOGIN_ROLE,
    TENANT_LOGIN_ROLE,
    RoleDatabase,
)


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


def current_role(connection: psycopg.Connection[tuple[object, ...]]) -> object:
    row = connection.execute("select current_user").fetchone()
    assert row is not None
    return row[0]


def test_a_platform_pin_serves_tenant_work_without_a_tenant_connection(
    role_urls: RoleDatabase,
) -> None:
    pools = role_urls.pools(max_size=1)
    held, release = threading.Event(), threading.Event()

    def hold_the_tenant_connection() -> None:
        with pools.tenant.connection():
            held.set()
            release.wait(10)

    holder = threading.Thread(target=hold_the_tenant_connection)
    holder.start()
    try:
        assert held.wait(10)
        # The tenant pool's one connection is taken: tenant work inside the
        # platform pin runs on the pin, never waiting for it.
        with (
            pools.platform.pinned_connection() as pinned,
            pools.tenant.connection() as lent,
        ):
            is_pinned = lent is pinned
            role_in_pin = current_role(lent)
    finally:
        release.set()
        holder.join()
    # A tenant pin borrows a connection of the platform pool instead.
    with pools.tenant.pinned_connection() as pinned:
        with pools.platform.connection() as borrowed:
            is_borrowed = borrowed is not pinned
            platform_role = current_role(borrowed)
        tenant_role = current_role(pinned)
    pools.close()

    assert (is_pinned, role_in_pin) == (True, PLATFORM_LOGIN_ROLE)
    assert (is_borrowed, platform_role) == (True, PLATFORM_LOGIN_ROLE)
    assert tenant_role == TENANT_LOGIN_ROLE
