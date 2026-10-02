"""
The cabinet's keyset pages and the dashboard's counts use their indexes on
tables of realistic size under forced row-level security: the statements
the repositories really run are recorded and replayed with EXPLAIN.
"""

from collections.abc import Generator
from contextlib import suppress

import pytest
from pydantic import ValidationError

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.hot_path_queries import INDEX_NODE_TYPES
from tests.storage.hot_path_seeding import (
    RecordingConnectionPool,
    analyze,
    explain,
    plan_nodes,
)
from tests.storage.list_query_plans import (
    BUSINESS,
    LIST_BUSINESS_IDS,
    LIST_QUERIES,
    ListQuery,
    ListRepositories,
)
from tests.storage.list_query_rows import seed_list_tables
from tests.storage.postgres_server import ThrowawayPostgresServer


@pytest.fixture(scope="module")
def list_database_url(
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
        seed_list_tables(connection_pool, LIST_BUSINESS_IDS)
        analyze(connection_pool)
        connection_pool.close()
        yield postgres_server.app_database_url(database_name)
    finally:
        connection_pool.close()
        postgres_server.drop_database(database_name)


@pytest.mark.parametrize("query", LIST_QUERIES, ids=lambda query: query.name)
def test_list_query_uses_its_index(
    list_database_url: DatabaseUrl, query: ListQuery
) -> None:
    recording_pool = RecordingConnectionPool(list_database_url)
    explaining_pool = PostgresConnectionPoolClient(list_database_url, max_size=1)
    storage_scope = StorageScopeContext()
    repositories = ListRepositories(recording_pool, storage_scope)
    try:
        # The seeded rows carry only their lookup fields and do not decode;
        # the recorded SQL is what this test checks.
        with (
            storage_scope.scoped_to_business(BUSINESS),
            suppress(ValidationError, ApplicationError),
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
    summary = [describe(plan) for plan in plans]
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
            and node.get("Index Name") == query.index
            for node in nodes
        ), f"{query.name}: {query.index} is not used: {summary}"


def describe(plan: dict[str, object]) -> list[str]:
    """The node types and indexes of a plan, for a readable failure."""

    return [
        f"{node['Node Type']}:{node.get('Index Name') or node.get('Relation Name')}"
        for node in plan_nodes(plan)
    ]
