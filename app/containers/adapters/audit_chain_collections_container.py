from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.compliance.audit_chain_purge_adapter_factory import (
    build_audit_chain_purge_adapter,
)
from app.containers.adapters.document_collection_provider import document_collection
from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.audit_chain_purges import AuditChainPurgeAdapterContract
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
    AuditViewCountDocument,
)


class AuditChainCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections around the audit log's hash chains (migration
    1193): counts of repeated views, the checkpoints purges leave, and the
    latest check of each chain. A sibling of DocumentCollectionsContainer
    with the same storage factory (Postgres with DATABASE_URL, else in
    memory); and the purge of a chain's oldest entries (the database's
    function, else its rules in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    audit_entry_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    audit_view_count_collection = document_collection(
        AuditViewCountDocument,
        "audit_view_counts",
        config,
        clients,
        utilities,
        time_provider,
    )
    audit_chain_checkpoint_collection = document_collection(
        AuditChainCheckpointDocument,
        "audit_chain_checkpoints",
        config,
        clients,
        utilities,
        time_provider,
    )
    audit_chain_status_collection = document_collection(
        AuditChainStatusDocument,
        "audit_chain_statuses",
        config,
        clients,
        utilities,
        time_provider,
    )
    audit_chain_purges: Singleton[AuditChainPurgeAdapterContract] = Singleton(
        build_audit_chain_purge_adapter,
        connection_pool=clients.postgres_pool,
        entries=audit_entry_collections.audit_log_entry_collection,
        checkpoints=audit_chain_checkpoint_collection,
        wall_clock=time_provider.microsecond_wall_clock,
    )
