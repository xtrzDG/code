"""Choose the purge of audit chains for the container wiring."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.compliance.in_memory_audit_chain_purge_adapter import (
    InMemoryAuditChainPurgeAdapter,
)
from app.adapters.compliance.postgres_audit_chain_purge_adapter import (
    RETENTION_PURGE_STATEMENT,
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
) -> AuditChainPurgeAdapterContract:
    """The database's purge function; without a database its rules in memory."""

    if connection_pool is None:
        return InMemoryAuditChainPurgeAdapter(entries, checkpoints, wall_clock)

    return PostgresAuditChainPurgeAdapter(connection_pool)


def build_audit_retention_purge_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
    checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
    wall_clock: WallClock[Microseconds],
) -> AuditChainPurgeAdapterContract:
    """
    The daily job's purge past the audit log's retention: the database's
    `workshop.purge_expired_audit_chain` on the platform pool (1250), which
    the application's platform role may call; without a database the same
    rules in memory.
    """

    if connection_pool is None:
        return InMemoryAuditChainPurgeAdapter(entries, checkpoints, wall_clock)

    return PostgresAuditChainPurgeAdapter(connection_pool, RETENTION_PURGE_STATEMENT)
