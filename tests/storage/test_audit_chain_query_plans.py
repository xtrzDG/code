"""
An append stays one key read however long its chain grows: on a seeded,
analyzed chain of thousands of entries under forced row-level security,
the statements an append really runs read the chain's head by its key
(`audit_chain_heads`, 1193) and never scan or sort the chain. They are
recorded and replayed with EXPLAIN (format json).
"""

from collections.abc import Generator

import pytest

from app.adapters.locks.postgres_advisory_lock_adapter import (
    PostgresAdvisoryLockAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
    AuditViewCountDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.compliance.audit_chain_hashing import (
    GENESIS_HASH,
    chain_key_of,
    link_entry_and_hash,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.compliance.audit_chain.audit_entries import entry
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.hot_path_seeding import (
    RecordingConnectionPool,
    analyze,
    explain,
    insert_documents,
    plan_nodes,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock

pytestmark = pytest.mark.postgres

LONG_CHAIN: BusinessId = BusinessId()
LONG_CHAIN_LENGTH: int = 4000
OTHER_CHAINS: int = 30
OTHER_CHAIN_LENGTH: int = 40
# As many chains as businesses: the heads are a table worth an index.
SHORT_CHAINS: int = 3000
CHAIN_SCANS: frozenset[str] = frozenset({"Seq Scan", "Bitmap Heap Scan"})
SORTS: frozenset[str] = frozenset({"Sort", "Incremental Sort"})


def linked_chain(
    business_id: BusinessId, length: int
) -> tuple[list[AuditLogEntryDocument], AuditChainHeadDocument]:
    """`length` linked entries of one business and the chain's head."""

    chain: list[AuditLogEntryDocument] = []
    previous = GENESIS_HASH
    for position in range(1, length + 1):
        linked, previous = link_entry_and_hash(
            entry(business_id, position), AuditChainPosition(position), previous
        )
        chain.append(linked)

    head = AuditChainHeadDocument(
        id=chain_key_of(business_id),
        business_id=business_id,
        head_position=AuditChainPosition(length),
        head_hash=previous,
        created_at=chain[0].created_at,
        updated_at=chain[-1].created_at,
    )
    return chain, head


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
        entries: list[AuditLogEntryDocument] = []
        heads: list[AuditChainHeadDocument] = []
        for business_id, length in (
            [(LONG_CHAIN, LONG_CHAIN_LENGTH)]
            + [(BusinessId(), OTHER_CHAIN_LENGTH) for _ in range(OTHER_CHAINS)]
            + [(BusinessId(), 1) for _ in range(SHORT_CHAINS)]
        ):
            chain, head = linked_chain(business_id, length)
            entries.extend(chain)
            heads.append(head)
        insert_documents(connection_pool, "audit_log_entries", entries)
        insert_documents(connection_pool, "audit_chain_heads", heads)
        analyze(connection_pool)
        connection_pool.close()
        yield postgres_server.app_database_url(database_name)
    finally:
        connection_pool.close()
        postgres_server.drop_database(database_name)


def test_an_append_to_a_long_chain_reads_its_head_by_key_and_sorts_nothing(
    seeded_database_url: DatabaseUrl,
) -> None:
    recording_pool = RecordingConnectionPool(seeded_database_url)
    explaining_pool = PostgresConnectionPoolClient(seeded_database_url, max_size=1)
    scope = StorageScopeContext()
    collections = PostgresCollectionFactory(
        connection_pool=recording_pool,
        storage_scope=scope,
        wall_clock=build_fixed_wall_clock(),
    )
    log = AuditLogRepository(
        collections(AuditLogEntryDocument, "audit_log_entries"),
        view_counts=collections(AuditViewCountDocument, "audit_view_counts"),
        checkpoints=collections(
            AuditChainCheckpointDocument, "audit_chain_checkpoints"
        ),
        heads=collections(AuditChainHeadDocument, "audit_chain_heads"),
        advisory_locks=PostgresAdvisoryLockAdapter(
            recording_pool, PostgresUnitOfWorkAdapter(recording_pool, scope)
        ),
    )
    appended = entry(LONG_CHAIN, LONG_CHAIN_LENGTH + 1, action=AuditAction.EXPORT)
    try:
        with scope.scoped_to_business(LONG_CHAIN):
            log.append(appended)
        plans = [
            plan
            for transaction in recording_pool.transactions
            for plan in explain(explaining_pool, transaction)
        ]
        stored = collections(AuditLogEntryDocument, "audit_log_entries")
        with scope.platform_wide():
            written = stored.get(str(appended.id))
    finally:
        recording_pool.close()
        explaining_pool.close()

    nodes = [node for plan in plans for node in plan_nodes(plan)]
    assert written is not None
    assert written.chain_position == AuditChainPosition(LONG_CHAIN_LENGTH + 1)
    assert any(
        node.get("Relation Name") == "audit_chain_heads"
        and node["Node Type"] == "Index Scan"
        and str(node.get("Index Name", "")).endswith("_pkey")
        for node in nodes
    ), f"the head is not read by its key: {plans}"
    assert not [
        node
        for node in nodes
        if node.get("Relation Name") == "audit_log_entries"
        and node["Node Type"] in CHAIN_SCANS
    ], f"the chain is scanned: {plans}"
    assert not [node for node in nodes if node["Node Type"] in SORTS], (
        f"an append sorts: {plans}"
    )
