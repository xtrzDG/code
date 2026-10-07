from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.business_exports import (
    BusinessExportDocument,
    ExportDownloadLinkDocument,
)
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.retention_purges import RetentionPurgeStateDocument
from app.schemas.domain.suppression import SuppressionEntryDocument


class PrivacyCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of data-subject rights (migration 1113): each
    business's suppression list, its full exports and their one-time
    download links (1134); and of retention
    (1123): its privacy settings and purge state. A sibling of
    DocumentCollectionsContainer with the same storage factory (Postgres
    with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    suppression_entry_collection = document_collection(
        SuppressionEntryDocument,
        "suppression_entries",
        config,
        clients,
        utilities,
        time_provider,
    )
    business_export_collection = document_collection(
        BusinessExportDocument,
        "business_exports",
        config,
        clients,
        utilities,
        time_provider,
    )
    export_download_link_collection = document_collection(
        ExportDownloadLinkDocument,
        "export_download_links",
        config,
        clients,
        utilities,
        time_provider,
    )
    business_privacy_settings_collection = document_collection(
        BusinessPrivacySettingsDocument,
        "business_privacy_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    retention_purge_state_collection = document_collection(
        RetentionPurgeStateDocument,
        "retention_purge_states",
        config,
        clients,
        utilities,
        time_provider,
    )
