"""
voice_health counts the voice platform's finished-call reports over every
business by the inbox's arrival index (1020), never by a sequential scan of
inbound_events.
"""

from collections.abc import Generator
from contextlib import suppress
from typing import LiteralString

import pytest
from psycopg import sql

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.repositories.voice_activity_repository import VoiceActivityRepository
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform_ops.ops_documents import HOUR, at
from tests.storage.hot_path_queries import INDEX_NODE_TYPES
from tests.storage.hot_path_seeding import (
    BYPASS_RLS,
    RecordingConnectionPool,
    analyze,
    explain,
    plan_nodes,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

ROWS: int = 20_000
# One event in ten is a call report; row n arrived n seconds before now.
SEED: LiteralString = (
    "insert into {table} "
    "(document_key, business_id, document, created_at, updated_at) "
    "select 'seeded_' || n, 'business_' || (n %% 30), jsonb_build_object("
    "'channel', case when n %% 10 = 0 then 'phone' else 'whatsapp' end, "
    "'created_at', %(now)s - n::bigint * 1000000), n, n "
    "from generate_series(1, %(rows)s) as n"
)


@pytest.fixture(scope="module")
def seeded_database_url(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
) -> Generator[DatabaseUrl]:
    name = postgres_server.create_database(template_name=migrated_template_database)
    pool = PostgresConnectionPoolClient(postgres_server.app_database_url(name))
    try:
        with pool.transaction() as connection:
            connection.execute(BYPASS_RLS)
            connection.execute(
                sql.SQL(SEED).format(
                    table=sql.Identifier("workshop", "inbound_events")
                ),
                {"rows": ROWS, "now": int(at(0))},
            )
        analyze(pool)
        pool.close()
        yield postgres_server.app_database_url(name)
    finally:
        pool.close()
        postgres_server.drop_database(name)


def test_post_call_reports_are_counted_by_the_arrival_index(
    seeded_database_url: DatabaseUrl,
) -> None:
    recording = RecordingConnectionPool(seeded_database_url)
    explaining = PostgresConnectionPoolClient(seeded_database_url, max_size=1)
    scope = StorageScopeContext()
    repository = VoiceActivityRepository(
        PostgresDocumentCollectionAdapter[InboundEventDocument](
            document_type=InboundEventDocument,
            collection_name=DocumentCollectionName("inbound_events"),
            connection_pools=PostgresConnectionPools.single(recording),
            storage_scope=scope,
            wall_clock=build_fixed_wall_clock(),
            isolation=infer_collection_isolation(InboundEventDocument),
        )
    )
    try:
        with scope.platform_wide(), suppress(ValueError, ApplicationError):
            repository.count_post_call_reports(
                ActivityWindow(since=at(-3 * HOUR), until=at(1))
            )
        plans = [
            plan
            for transaction in recording.transactions
            for plan in explain(explaining, transaction)
        ]
    finally:
        recording.close()
        explaining.close()

    assert plans, "the repository ran no query"
    for plan in plans:
        nodes = plan_nodes(plan)
        assert not [
            node
            for node in nodes
            if node["Node Type"] == "Seq Scan"
            and node.get("Relation Name") == "inbound_events"
        ], f"sequential scan of inbound_events: {plan}"
        assert any(node["Node Type"] in INDEX_NODE_TYPES for node in nodes), plan
