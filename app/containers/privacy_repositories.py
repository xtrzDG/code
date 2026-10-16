from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.privacy_collections_container import (
    PrivacyCollectionsContainer,
)
from app.repositories.privacy_repositories import (
    BusinessExportRepository,
    ExportDownloadLinkRepository,
    SuppressionEntryRepository,
)
from app.repositories.retention_settings_repositories import (
    BusinessPrivacySettingsRepository,
    RetentionPurgeStateRepository,
)


class PrivacyRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of data-subject rights (migration 1113): the
    suppression list, the full business exports and their one-time
    download links (1134); and of retention
    (1123): each business's privacy settings and purge state.
    `RepositoriesContainer`
    extends it, so they are read as `repositories.suppression_entry_repo`
    like every other repository.
    """

    privacy_collections: PrivacyCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    suppression_entry_repo: Singleton[SuppressionEntryRepository] = Singleton(
        SuppressionEntryRepository,
        collection=privacy_collections.suppression_entry_collection,
    )
    business_export_repo: Singleton[BusinessExportRepository] = Singleton(
        BusinessExportRepository,
        collection=privacy_collections.business_export_collection,
    )
    export_download_link_repo: Singleton[ExportDownloadLinkRepository] = Singleton(
        ExportDownloadLinkRepository,
        collection=privacy_collections.export_download_link_collection,
    )
    privacy_settings_repo: Singleton[BusinessPrivacySettingsRepository] = Singleton(
        BusinessPrivacySettingsRepository,
        collection=privacy_collections.business_privacy_settings_collection,
    )
    retention_purge_state_repo: Singleton[RetentionPurgeStateRepository] = Singleton(
        RetentionPurgeStateRepository,
        collection=privacy_collections.retention_purge_state_collection,
    )
