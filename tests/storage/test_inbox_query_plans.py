"""
The team inbox's views, counts, notes and open work use their indexes on
tables of realistic size under forced row-level security (migration 1053):
the statements the repositories really run are recorded and replayed with
EXPLAIN.
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
from tests.storage.inbox_query_plans import (
    INBOX_QUERIES,
    INBOX_TABLES,
    InboxPlanQuery,
    InboxRepositories,
)
from tests.storage.list_query_plans import BUSINESS, LIST_BUSINESS_IDS
from tests.storage.list_query_rows import seed_list_tables
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.test_list_query_plans import describe


@pytest.fixture(scope="module")
def inbox_database_url(
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
        seed_list_tables(connection_pool, LIST_BUSINESS_IDS, INBOX_TABLES)
        analyze(connection_pool)
        connection_pool.close()
        yield postgres_server.app_database_url(database_name)
    finally:
        connection_pool.close()
        postgres_server.drop_database(database_name)


@pytest.mark.parametrize("query", INBOX_QUERIES, ids=lambda query: query.name)
def test_inbox_query_uses_its_index(
    inbox_database_url: DatabaseUrl, query: InboxPlanQuery
) -> None:
    recording_pool = RecordingConnectionPool(inbox_database_url)
    explaining_pool = PostgresConnectionPoolClient(inbox_database_url, max_size=1)
    storage_scope = StorageScopeContext()
    repositories = InboxRepositories(recording_pool, storage_scope)
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
