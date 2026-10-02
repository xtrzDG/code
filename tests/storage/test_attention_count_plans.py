"""
The navigation badges stay cheap: each attention count is an index lookup
of the business and a status (migration 1040), on tables of realistic size
under forced row-level security, never a scan of the business's rows.
"""

from collections.abc import Callable, Generator
from typing import LiteralString

import pytest
from psycopg import sql
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.attention_count_repository import AttentionCountRepository
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
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

ROWS_PER_TABLE: int = 6_000
BUSINESSES: list[BusinessId] = [BusinessId() for _ in range(30)]
NOW: Microseconds = Microseconds(1_790_812_800_000_000)
STATUSES: dict[str, LiteralString] = {
    "handoffs": "(array['pending', 'notified', 'notification_failed', 'resolved',"
    " 'resolved', 'resolved', 'resolved', 'resolved'])[1 + (n / 30) %% 8]",
    "leads": "(array['new', 'in_progress', 'won', 'lost', 'won', 'lost'])"
    "[1 + (n / 30) %% 6]",
    "bookings": "(array['pending', 'confirmed', 'confirmed', 'completed',"
    " 'cancelled', 'no_show'])[1 + (n / 30) %% 6]",
    "channels": "(array['connected', 'connected', 'disabled', 'error'])"
    "[1 + (n / 30) %% 4]",
}
type CountQuery = Callable[[AttentionCountRepository, BusinessId], object]
COUNT_QUERIES: dict[str, tuple[CountQuery, str]] = {
    "open handoffs": (
        lambda repo, business: repo.count_open_handoffs(business),
        "handoffs_doc_status_idx",
    ),
    "new leads": (
        lambda repo, business: repo.count_new_leads(business),
        "leads_doc_status_idx",
    ),
    "unconfirmed bookings": (
        lambda repo, business: repo.count_unconfirmed_bookings(business, NOW),
        "bookings_doc_status_starts_at_idx",
    ),
    "failing channels": (
        lambda repo, business: repo.count_failing_channels(business),
        "channels_doc_status_idx",
    ),
}


def seed(connection_pool: PostgresConnectionPoolClient) -> None:
    with connection_pool.transaction() as connection:
        connection.execute(BYPASS_RLS)
        for table, status_sql in STATUSES.items():
            statement: LiteralString = (
                "insert into {table} "
                "(document_key, business_id, document, created_at, updated_at) "
                "select 'seeded_' || n, (%(businesses)s::text[])[1 + n %% 30], "
                f"jsonb_build_object('status', {status_sql}, "
                "'is_sandbox', (n / 30) %% 7 = 0, "
                "'starts_at', %(seconds)s + n * 60), n, n "
                "from generate_series(1, %(rows)s) as n"
            )
            connection.execute(
                sql.SQL(statement).format(table=sql.Identifier("workshop", table)),
                {
                    "businesses": [str(business) for business in BUSINESSES],
                    "rows": ROWS_PER_TABLE,
                    "seconds": int(NOW) // 1_000_000 - ROWS_PER_TABLE * 30,
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


def attention_repository(
    pool: PostgresConnectionPoolClient, scope: StorageScopeContext
) -> AttentionCountRepository:
    def collection[
        Document: HandoffDocument | LeadDocument | BookingDocument | ChannelDocument
    ](
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

    return AttentionCountRepository(
        collection(HandoffDocument, "handoffs"),
        collection(LeadDocument, "leads"),
        collection(BookingDocument, "bookings"),
        collection(ChannelDocument, "channels"),
    )


@pytest.mark.parametrize("name", list(COUNT_QUERIES))
def test_an_attention_count_uses_its_index(
    seeded_database_url: DatabaseUrl, name: str
) -> None:
    run, index = COUNT_QUERIES[name]
    table: str = index.split("_doc_")[0]
    recording = RecordingConnectionPool(seeded_database_url)
    explaining = PostgresConnectionPoolClient(seeded_database_url, max_size=1)
    scope = StorageScopeContext()
    try:
        with scope.scoped_to_business(BUSINESSES[0]):
            count = run(attention_repository(recording, scope), BUSINESSES[0])
        plans = [
            plan
            for transaction in recording.transactions
            for plan in explain(explaining, transaction)
        ]
    finally:
        recording.close()
        explaining.close()

    assert isinstance(count, int) and count > 0
    assert plans
    for plan in plans:
        nodes = plan_nodes(plan)
        assert not [
            node
            for node in nodes
            if node["Node Type"] == "Seq Scan" and node.get("Relation Name") == table
        ], f"{name}: sequential scan of {table}: {plan}"
        assert any(
            node["Node Type"] in INDEX_NODE_TYPES and node.get("Index Name") == index
            for node in nodes
        ), f"{name}: {index} is not used: {plan}"
