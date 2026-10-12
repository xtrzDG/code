"""The audit log, its chains and its reads across businesses, in memory."""

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.audit.audit_activity_repository import AuditActivityRepository
from app.repositories.audit.audit_chain_repository import AuditChainRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
    AuditViewCountDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument


class AuditTrailStore:
    """One audit log and the repositories that read it, sharing storage."""

    def __init__(self) -> None:
        self.entries = InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
            AuditLogEntryDocument
        )
        self.view_counts = InMemoryDocumentCollectionAdapter[AuditViewCountDocument](
            AuditViewCountDocument
        )
        self.checkpoints = InMemoryDocumentCollectionAdapter[
            AuditChainCheckpointDocument
        ](AuditChainCheckpointDocument)
        self.statuses = InMemoryDocumentCollectionAdapter[AuditChainStatusDocument](
            AuditChainStatusDocument
        )
        self.log = AuditLogRepository(
            self.entries,
            view_counts=self.view_counts,
            checkpoints=self.checkpoints,
            advisory_locks=InMemoryAdvisoryLockAdapter(),
        )
        self.chains = AuditChainRepository(
            self.entries, checkpoints=self.checkpoints, statuses=self.statuses
        )
        self.activity = AuditActivityRepository(self.entries)
