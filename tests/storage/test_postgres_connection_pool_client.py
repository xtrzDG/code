"""The thread-safe connection pool against a real Postgres."""

import threading
import time

import psycopg
import pytest
from psycopg import pq

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.users import UserDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock


def backend_pid(connection_pool: PostgresConnectionPoolClient) -> int:
    with connection_pool.connection() as connection:
        row = connection.execute("select pg_backend_pid()").fetchone()

    assert row is not None
    pid: object = row[0]
    assert isinstance(pid, int)
    return pid


def terminate_backend(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    pid: int,
) -> None:
    with postgres_server.admin_connection(database_name) as connection:
        connection.execute("select pg_terminate_backend(%s)", (pid,))

    # Give the backend a moment to exit and close the socket.
    time.sleep(0.2)


def test_connections_are_reused(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=3)
    try:
        first_pid = backend_pid(connection_pool)
        second_pid = backend_pid(connection_pool)

        assert first_pid == second_pid
        assert connection_pool.open_connection_count() == 1
        assert connection_pool.idle_connection_count() == 1
        assert connection_pool.max_size == 3
    finally:
        connection_pool.close()

    assert connection_pool.open_connection_count() == 0


def test_transaction_commits_and_rolls_back(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        with connection_pool.transaction() as connection:
            connection.execute("create table committed (value int)")

        with (
            pytest.raises(RuntimeError, match="stop"),
            connection_pool.transaction() as connection,
        ):
            connection.execute("create table rolled_back (value int)")
            raise RuntimeError("stop")

        with connection_pool.connection() as connection:
            row = connection.execute(
                "select to_regclass('committed') is not null, "
                "to_regclass('rolled_back') is not null"
            ).fetchone()
    finally:
        connection_pool.close()

    assert row == (True, False)


def test_open_transaction_is_rolled_back_on_release(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        with connection_pool.connection() as connection:
            connection.execute("begin")
            connection.execute("create table never_committed (value int)")
            assert connection.info.transaction_status is pq.TransactionStatus.INTRANS

        with connection_pool.connection() as connection:
            assert connection.info.transaction_status is pq.TransactionStatus.IDLE
            row = connection.execute(
                "select to_regclass('never_committed') is not null"
            ).fetchone()
    finally:
        connection_pool.close()

    assert row == (False,)


def test_waiting_for_a_busy_pool_times_out(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=1,
        acquire_timeout_seconds=0.2,
    )
    try:
        with connection_pool.connection():
            started = time.monotonic()
            with (
                pytest.raises(ExternalServiceError, match="No free database"),
                connection_pool.connection(),
            ):
                pass
            assert time.monotonic() - started >= 0.15

        assert connection_pool.open_connection_count() == 1
    finally:
        connection_pool.close()


def test_waiter_gets_the_connection_when_it_is_released(
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=1,
        acquire_timeout_seconds=10,
    )
    holder_ready = threading.Event()
    waiter_pids: list[int] = []

    def wait_for_connection() -> None:
        holder_ready.wait()
        waiter_pids.append(backend_pid(connection_pool))

    waiter = threading.Thread(target=wait_for_connection)
    try:
        waiter.start()
        with connection_pool.connection() as connection:
            row = connection.execute("select pg_backend_pid()").fetchone()
            holder_ready.set()
            time.sleep(0.2)
            assert waiter_pids == []
        waiter.join(timeout=10)
    finally:
        connection_pool.close()

    assert row is not None
    assert waiter_pids == [row[0]]


def test_broken_connection_is_discarded(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=1,
        idle_check_seconds=3600,
    )
    try:
        first_pid = backend_pid(connection_pool)
        terminate_backend(postgres_server, database_name, first_pid)

        # Not pinged (fresh idle connection): the first use fails...
        with (
            pytest.raises(psycopg.OperationalError),
            connection_pool.connection() as connection,
        ):
            connection.execute("select 1")

        # ...and the broken connection does not come back.
        assert connection_pool.open_connection_count() == 0
        assert backend_pid(connection_pool) != first_pid
    finally:
        connection_pool.close()


def test_lost_connection_surfaces_as_external_service_error_once(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=1,
        idle_check_seconds=3600,
    )
    try:
        users = PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_fixed_wall_clock(),
        )(UserDocument, "users")
        first_pid = backend_pid(connection_pool)
        terminate_backend(postgres_server, database_name, first_pid)

        with pytest.raises(ExternalServiceError, match="users"):
            users.list_all()

        assert users.list_all() == []
    finally:
        connection_pool.close()


def test_idle_connection_is_pinged_and_replaced(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=1,
        idle_check_seconds=0,
    )
    try:
        first_pid = backend_pid(connection_pool)
        terminate_backend(postgres_server, database_name, first_pid)

        second_pid = backend_pid(connection_pool)

        assert second_pid != first_pid
        assert connection_pool.open_connection_count() == 1
    finally:
        connection_pool.close()


def test_closed_pool_refuses_new_work(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=2)
    with connection_pool.connection() as borrowed_connection:
        connection_pool.close()
        borrowed_connection.execute("select 1")

    assert borrowed_connection.closed
    assert connection_pool.open_connection_count() == 0
    with (
        pytest.raises(ExternalServiceError, match="closed"),
        connection_pool.connection(),
    ):
        pass


def test_unreachable_database_is_an_external_service_error(
    postgres_server: ThrowawayPostgresServer,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        DatabaseUrl(postgres_server.conninfo("database_that_does_not_exist", "nobody")),
        max_size=1,
        connect_timeout_seconds=2,
    )

    with (
        pytest.raises(ExternalServiceError, match="Could not connect"),
        connection_pool.connection(),
    ):
        pass

    assert connection_pool.open_connection_count() == 0


def test_pool_needs_room_for_one_connection() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PostgresConnectionPoolClient(DatabaseUrl("host=/nowhere"), max_size=0)
