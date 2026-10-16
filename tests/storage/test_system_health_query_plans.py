"""
The admin system page and the platform alerts read only indexed counts and
short indexed lists: each platform-wide query uses an index of migration
1093 (or older ones) on tables of realistic size under forced row-level
security, never a sequential scan.
"""

from collections.abc import Callable, Generator
from contextlib import suppress
from typing import LiteralString

import pytest
from base_pydantic_schemas import PersistentDocument
from psycopg import sql

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.platform_activity_repository import PlatformActivityRepository
from app.repositories.system_health_repository import SystemHealthRepository
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform_ops.ops_documents import DAY, HOUR, at
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
BUSINESSES: list[BusinessId] = [BusinessId() for _ in range(30)]
# Row n was written n seconds before NOW - 1 h (the last hour stays sparse).
TIME: LiteralString = "(%(now)s - 3600000000 - n::bigint * 1000000)"
SEEDED: dict[str, LiteralString] = {
    "queued_jobs": "jsonb_build_object('status', case when n %% 500 = 0 then "
    "'dead' when n %% 97 = 0 then 'pending' else 'done' end, "
    "'lane', (array['inbound', 'outbound', 'default'])[1 + n %% 3], "
    f"'name', 'job_' || (n %% 7), 'run_at', {TIME})",
    "channels": "jsonb_build_object('status', case when n %% 400 = 0 then "
    "'error' else 'connected' end, 'credential_expires_at', case when "
    f"n %% 300 = 0 then {TIME} + 40 * 86400000000 end)",
    "handoffs": f"jsonb_build_object('is_sandbox', n %% 9 = 0, 'created_at', {TIME})",
    "outbound_messages": "jsonb_build_object('status', (array['delivered', "
    f"'delivered', 'dead', 'pending'])[1 + n %% 4], 'created_at', {TIME})",
    "messages": "jsonb_build_object('created_at', "
    f"{TIME}, 'tool_calls', case when n %% 20 = 0 then jsonb_build_array("
    "jsonb_build_object('is_error', n %% 40 = 0)) else '[]'::jsonb end)",
}
LAST_HOUR: ActivityWindow = ActivityWindow(since=at(-HOUR), until=at(1))
LIMIT: DocumentQueryLimit = DocumentQueryLimit(20)
type Query = Callable[[SystemHealthRepository, PlatformActivityRepository], object]
QUERIES: dict[str, tuple[Query, str]] = {
    "open jobs by state and lane": (lambda h, a: h.count_open_jobs(), "queued_jobs"),
    "due jobs of a lane": (
        lambda h, a: h.count_due_jobs(JobLane.INBOUND, at(0)),
        "queued_jobs",
    ),
    "oldest due job": (
        lambda h, a: h.find_oldest_due_job(JobLane.INBOUND, at(0)),
        "queued_jobs",
    ),
    "dead letters by name": (lambda h, a: h.count_dead_jobs_by_name(), "queued_jobs"),
    "channels in error": (lambda h, a: h.list_channels_in_error(LIMIT), "channels"),
    "count of channels in error": (
        lambda h, a: h.count_channels_in_error(),
        "channels",
    ),
    "expiring tokens": (
        lambda h, a: h.list_credentials_expiring_before(at(14 * DAY), LIMIT),
        "channels",
    ),
    "handoffs of the last hour": (lambda h, a: a.count_handoffs(LAST_HOUR), "handoffs"),
    "outbox by state": (lambda h, a: a.count_outbound(LAST_HOUR), "outbound_messages"),
    "failed tool calls": (
        lambda h, a: a.count_tool_error_messages(LAST_HOUR),
        "messages",
    ),
}


def seed(pool: PostgresConnectionPoolClient) -> None:
    with pool.transaction() as connection:
        connection.execute(BYPASS_RLS)
        for table, document_sql in SEEDED.items():
            statement: LiteralString = (
                "insert into {table} "
                "(document_key, business_id, document, created_at, updated_at) "
                "select 'seeded_' || n, (%(businesses)s::text[])[1 + n %% 30], "
                f"{document_sql}, n, n from generate_series(1, %(rows)s) as n"
            )
            connection.execute(
                sql.SQL(statement).format(table=sql.Identifier("workshop", table)),
                {
                    "businesses": [str(business) for business in BUSINESSES],
                    "rows": ROWS,
                    "now": int(at(0)),
                },
            )


@pytest.fixture(scope="module")
def seeded_database_url(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
) -> Generator[DatabaseUrl]:
    name = postgres_server.create_database(template_name=migrated_template_database)
    pool = PostgresConnectionPoolClient(postgres_server.app_database_url(name))
    try:
        seed(pool)
        analyze(pool)
        pool.close()
        yield postgres_server.app_database_url(name)
    finally:
        pool.close()
        postgres_server.drop_database(name)


def repositories(
    pool: PostgresConnectionPoolClient, scope: StorageScopeContext
) -> tuple[SystemHealthRepository, PlatformActivityRepository]:
    def collection[Document: PersistentDocument](
        document_type: type[Document], name: str
    ) -> PostgresDocumentCollectionAdapter[Document]:
        return PostgresDocumentCollectionAdapter[Document](
            document_type=document_type,
            collection_name=DocumentCollectionName(name),
            connection_pool=pool,
            storage_scope=scope,
            wall_clock=build_fixed_wall_clock(),
            isolation=infer_collection_isolation(document_type),
        )

    return (
        SystemHealthRepository(
            collection(QueuedJobDocument, "queued_jobs"),
            collection(WorkerHeartbeatDocument, "worker_heartbeats"),
            collection(ChannelDocument, "channels"),
            collection(BusinessDocument, "businesses"),
        ),
        PlatformActivityRepository(
            collection(HandoffDocument, "handoffs"),
            collection(OutboundMessageDocument, "outbound_messages"),
            collection(MessageDocument, "messages"),
        ),
    )


@pytest.mark.parametrize("name", sorted(QUERIES))
def test_platform_wide_counts_use_an_index(
    seeded_database_url: DatabaseUrl, name: str
) -> None:
    query, table = QUERIES[name]
    recording = RecordingConnectionPool(seeded_database_url)
    explaining = PostgresConnectionPoolClient(seeded_database_url, max_size=1)
    scope = StorageScopeContext()
    health, activity = repositories(recording, scope)
    try:
        # Seeded rows carry only their lookup fields: the SQL is what counts.
        with scope.platform_wide(), suppress(ValueError, ApplicationError):
            query(health, activity)
        plans = [
            plan
            for transaction in recording.transactions
            for plan in explain(explaining, transaction)
        ]
    finally:
        recording.close()
        explaining.close()

    assert plans, f"{name}: the repository ran no query"
    for plan in plans:
        nodes = plan_nodes(plan)
        scans = [
            node
            for node in nodes
            if node["Node Type"] == "Seq Scan" and node.get("Relation Name") == table
        ]
        assert not scans, f"{name}: sequential scan of {table}: {plan}"
        assert any(node["Node Type"] in INDEX_NODE_TYPES for node in nodes), (
            f"{name}: no index is used: {plan}"
        )
