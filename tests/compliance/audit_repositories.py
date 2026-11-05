"""The audit log repository over in-memory storage, for tests."""

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
    AuditViewCountDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument


def audit_log_repository(
    entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] | None = None,
    view_counts: DocumentCollectionAdapterContract[AuditViewCountDocument]
    | None = None,
    checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument]
    | None = None,
    advisory_locks: AdvisoryLockAdapterContract | None = None,
) -> AuditLogRepository:
    """The audit log over `entries` (in memory when not given)."""

    return AuditLogRepository(
        (
            InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
            if entries is None
            else entries
        ),
        view_counts=(
            InMemoryDocumentCollectionAdapter(AuditViewCountDocument)
            if view_counts is None
            else view_counts
        ),
        checkpoints=(
            InMemoryDocumentCollectionAdapter(AuditChainCheckpointDocument)
            if checkpoints is None
            else checkpoints
        ),
        heads=InMemoryDocumentCollectionAdapter(AuditChainHeadDocument),
        advisory_locks=(
            InMemoryAdvisoryLockAdapter() if advisory_locks is None else advisory_locks
        ),
    )
