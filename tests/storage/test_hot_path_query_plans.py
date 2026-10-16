"""
Every hot query uses an index, on tables of realistic size under forced
row-level security: the statements the repositories really run are
recorded and replayed with EXPLAIN (format json).
"""

from collections.abc import Generator

import pytest

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.hot_path_queries import (
    BUSINESS_IDS,
    HOT_QUERIES,
    INDEX_NODE_TYPES,
    HotQuery,
)
from tests.storage.hot_path_repositories import HotPathRepositories
from tests.storage.hot_path_rows import seed_hot_path_tables
from tests.storage.hot_path_seeding import (
    RecordingConnectionPool,
    analyze,
    explain,
    plan_nodes,
)
from tests.storage.postgres_server import ThrowawayPostgresServer


@pytest.fixture(scope="module")
def seeded_database_url(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
) -> Generator[DatabaseUrl]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    connection_pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(database_name), max_size=1
    )
    try:
        seed_hot_path_tables(connection_pool, BUSINESS_IDS)
        analyze(connection_pool)
        connection_pool.close()
        yield postgres_server.app_database_url(database_name)
    finally:
        connection_pool.close()
        postgres_server.drop_database(database_name)


@pytest.mark.parametrize("query", HOT_QUERIES, ids=lambda query: query.name)
def test_hot_query_uses_its_index(
    seeded_database_url: DatabaseUrl,
    query: HotQuery,
) -> None:
    recording_pool = RecordingConnectionPool(seeded_database_url)
    explaining_pool = PostgresConnectionPoolClient(seeded_database_url, max_size=1)
    storage_scope = StorageScopeContext()
    repositories = HotPathRepositories(recording_pool, storage_scope)
    try:
        # Platform-level queries (webhook routing, purges) run platform-wide.
        with (
            storage_scope.scoped_to_business(BUSINESS_IDS[0])
            if query.is_in_business_scope
            else storage_scope.platform_wide()
        ):
            query.run(repositories)

        plans = [
            plan
            for transaction in recording_pool.transactions
            for plan in explain(explaining_pool, transaction)
        ]
    finally:
        recording_pool.close()
        explaining_pool.close()

    assert plans, "the repository ran no query"
    for plan in plans:
        nodes = plan_nodes(plan)
        assert not [
            node
            for node in nodes
            if node["Node Type"] == "Seq Scan"
            and node.get("Relation Name") == query.table
        ], f"{query.name}: sequential scan of {query.table}: {plan}"
        assert any(
            node["Node Type"] in INDEX_NODE_TYPES
            and node.get("Index Name") in {query.index, *query.alternative_indexes}
            for node in nodes
        ), f"{query.name}: {query.index} is not used: {plan}"
