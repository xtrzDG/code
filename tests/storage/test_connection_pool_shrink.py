"""
After a burst the pool closes the connections it no longer needs: one idle
for `max_idle_seconds` is closed the next time the pool is used, down to
`min_size`, so a process does not keep its peak and a deploy's overlap fits
the server's connection limit (docs/operations/capacity.md).
"""

import threading
import time

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from tests.storage.postgres_server import ThrowawayPostgresServer

IDLE_SECONDS: float = 0.2
BURST: int = 4


def borrow_together(pool: PostgresConnectionPoolClient, count: int) -> None:
    """`count` threads hold a connection at the same moment, then return it."""

    barrier = threading.Barrier(count)

    def hold() -> None:
        with pool.connection() as connection:
            connection.execute("select 1")
            barrier.wait(timeout=10)

    threads = [threading.Thread(target=hold) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)


def server_sessions(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> int:
    with postgres_server.admin_connection(database_name) as connection:
        row = connection.execute(
            "select count(*) from pg_stat_activity "
            "where datname = %s and application_name = 'assistant-workshop'",
            (database_name,),
        ).fetchone()

    assert row is not None
    return int(row[0])


def test_idle_connections_close_down_to_the_minimum(
    database_url: DatabaseUrl,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    pool = PostgresConnectionPoolClient(
        database_url, max_size=BURST, min_size=1, max_idle_seconds=IDLE_SECONDS
    )
    try:
        borrow_together(pool, BURST)
        assert pool.open_connection_count() == BURST
        assert server_sessions(postgres_server, database_name) == BURST

        time.sleep(IDLE_SECONDS * 2)
        with pool.connection() as connection:
            connection.execute("select 1")

        # The minimum stays open for the next request; the rest are gone.
        assert pool.open_connection_count() == 1
        assert server_sessions(postgres_server, database_name) == 1
    finally:
        pool.close()


def test_connections_in_steady_use_are_kept(database_url: DatabaseUrl) -> None:
    pool = PostgresConnectionPoolClient(
        database_url, max_size=BURST, min_size=0, max_idle_seconds=60.0
    )
    try:
        borrow_together(pool, 3)
        for _ in range(5):
            with pool.connection() as connection:
                connection.execute("select 1")

        assert pool.open_connection_count() == 3
        assert pool.idle_connection_count() == 3
    finally:
        pool.close()


def test_without_an_idle_limit_the_pool_keeps_its_connections(
    database_url: DatabaseUrl,
) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=BURST)
    try:
        borrow_together(pool, 2)
        time.sleep(IDLE_SECONDS)
        with pool.connection() as connection:
            connection.execute("select 1")

        assert pool.open_connection_count() == 2
    finally:
        pool.close()


def test_a_minimum_above_the_size_keeps_every_connection(
    database_url: DatabaseUrl,
) -> None:
    pool = PostgresConnectionPoolClient(
        database_url, max_size=2, min_size=9, max_idle_seconds=IDLE_SECONDS
    )
    try:
        borrow_together(pool, 2)
        time.sleep(IDLE_SECONDS * 2)
        with pool.connection() as connection:
            connection.execute("select 1")

        assert pool.open_connection_count() == 2
    finally:
        pool.close()
