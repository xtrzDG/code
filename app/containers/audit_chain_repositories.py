from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.adapters.audit_chain_collections_container import (
    AuditChainCollectionsContainer,
)
from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.repositories.audit.audit_activity_repository import AuditActivityRepository
from app.repositories.audit.audit_chain_repository import AuditChainRepository
from app.repositories.compliance_repositories import AuditLogRepository


class AuditChainRepositoriesContainer(containers.DeclarativeContainer):
    """
    The audit log (append-only and hash-chained, migration 1193), the reads
    of its chains' checks and the reads across businesses of the admin
    audit view and the anomaly alerts. `RepositoriesContainer` extends it,
    so they are read as `repositories.audit_log_repo` like every other
    repository.
    """

    audit_chain_collections: AuditChainCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    audit_entry_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    audit_adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]

    audit_log_repo: Singleton[AuditLogRepository] = Singleton(
        AuditLogRepository,
        collection=audit_entry_collections.audit_log_entry_collection,
        view_counts=audit_chain_collections.audit_view_count_collection,
        checkpoints=audit_chain_collections.audit_chain_checkpoint_collection,
        heads=audit_chain_collections.audit_chain_head_collection,
        advisory_locks=audit_adapters.advisory_locks,
    )
    audit_chain_repo: Singleton[AuditChainRepository] = Singleton(
        AuditChainRepository,
        entries=audit_entry_collections.audit_log_entry_collection,
        checkpoints=audit_chain_collections.audit_chain_checkpoint_collection,
        statuses=audit_chain_collections.audit_chain_status_collection,
    )
    audit_activity_repo: Singleton[AuditActivityRepository] = Singleton(
        AuditActivityRepository,
        collection=audit_entry_collections.audit_log_entry_collection,
    )
    # The purge of a chain's oldest entries (`workshop purge-audit-log`).
    audit_chain_purges = audit_chain_collections.audit_chain_purges
