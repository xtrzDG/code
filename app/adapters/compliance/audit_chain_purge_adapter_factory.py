"""Choose the purge of audit chains for the container wiring."""

from typing import LiteralString

from typed_time_provider import Microseconds, WallClock

from app.adapters.compliance.in_memory_audit_chain_purge_adapter import (
    InMemoryAuditChainPurgeAdapter,
)
from app.adapters.compliance.postgres_audit_chain_purge_adapter import (
    PURGE_STATEMENT,
    PostgresAuditChainPurgeAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.audit_chain_purges import AuditChainPurgeAdapterContract
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.domain.audit_chain import AuditChainCheckpointDocument
from app.schemas.domain.compliance import AuditLogEntryDocument


def build_audit_chain_purge_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
    checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
    wall_clock: WallClock[Microseconds],
    statement: LiteralString = PURGE_STATEMENT,
) -> AuditChainPurgeAdapterContract:
    """
    The database's purge function (`statement`: the operator's, or the
    daily job's `RETENTION_PURGE_STATEMENT` on the platform pool, 1250);
    without a database its rules in memory.
    """

    if connection_pool is None:
        return InMemoryAuditChainPurgeAdapter(entries, checkpoints, wall_clock)

    return PostgresAuditChainPurgeAdapter(connection_pool, statement)
