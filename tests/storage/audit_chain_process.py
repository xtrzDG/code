"""
What one API process has for the audit log on Postgres: its own pool,
storage scope, advisory locks, collections and repositories. Two of them
over one database are two processes' sessions.
"""

from app.adapters.compliance.postgres_audit_chain_purge_adapter import (
    PostgresAuditChainPurgeAdapter,
)
from app.adapters.locks.postgres_advisory_lock_adapter import (
    PostgresAdvisoryLockAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.repositories.audit.audit_activity_repository import AuditActivityRepository
from app.repositories.audit.audit_chain_repository import AuditChainRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
    AuditChainStatusDocument,
    AuditViewCountDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import build_fixed_wall_clock


class AuditProcess:
    """The audit log as one process sees it."""

    def __init__(
        self,
        database_url: DatabaseUrl,
        entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] | None = None,
    ) -> None:
        self.pool = PostgresConnectionPoolClient(database_url, max_size=4)
        self.scope = StorageScopeContext()
        collections = PostgresCollectionFactory(
            connection_pool=self.pool,
            storage_scope=self.scope,
            wall_clock=build_fixed_wall_clock(),
        )
        self.entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            collections(AuditLogEntryDocument, "audit_log_entries")
            if entries is None
            else entries
        )
        checkpoints = collections(
            AuditChainCheckpointDocument, "audit_chain_checkpoints"
        )
        self.heads: DocumentCollectionAdapterContract[AuditChainHeadDocument] = (
            collections(AuditChainHeadDocument, "audit_chain_heads")
        )
        self.log = AuditLogRepository(
            self.entries,
            view_counts=collections(AuditViewCountDocument, "audit_view_counts"),
            checkpoints=checkpoints,
            heads=self.heads,
            advisory_locks=PostgresAdvisoryLockAdapter(
                self.pool, PostgresUnitOfWorkAdapter(self.pool, self.scope)
            ),
        )
        self.chains = AuditChainRepository(
            self.entries,
            checkpoints=checkpoints,
            statuses=collections(AuditChainStatusDocument, "audit_chain_statuses"),
        )
        self.activity = AuditActivityRepository(self.entries)
        self.purges = PostgresAuditChainPurgeAdapter(self.pool)

    def close(self) -> None:
        self.pool.close()
