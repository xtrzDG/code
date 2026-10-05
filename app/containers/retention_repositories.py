from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.call_adapters_container import CallAdaptersContainer
from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.privacy_collections_container import (
    PrivacyCollectionsContainer,
)
from app.repositories.retention_record_repositories import (
    ExpiredLlmTurnRepository,
    ExpiredMessageRepository,
    ExpiredMissedCallRepository,
    ExpiringBookingRepository,
    ExpiringHandoffRepository,
    ExpiringLeadRepository,
    QuietConversationRepository,
)
from app.repositories.retention_settings_repositories import (
    BusinessPrivacySettingsRepository,
    RetentionPurgeStateRepository,
)


class RetentionRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the retention engine (migration 1123): each
    business's privacy settings and purge state, and the purge's reads and
    batched deletes over the conversation, booking and call collections.
    `RepositoriesContainer` extends it, so they are read as
    `repositories.privacy_settings_repo` like every other repository.
    """

    collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    privacy_collections: PrivacyCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    call_adapters: CallAdaptersContainer = DependenciesContainer()  # type: ignore[assignment]

    privacy_settings_repo: Singleton[BusinessPrivacySettingsRepository] = Singleton(
        BusinessPrivacySettingsRepository,
        collection=privacy_collections.business_privacy_settings_collection,
    )
    retention_purge_state_repo: Singleton[RetentionPurgeStateRepository] = Singleton(
        RetentionPurgeStateRepository,
        collection=privacy_collections.retention_purge_state_collection,
    )
    quiet_conversation_repo: Singleton[QuietConversationRepository] = Singleton(
        QuietConversationRepository, collection=collections.conversation_collection
    )
    expired_message_repo: Singleton[ExpiredMessageRepository] = Singleton(
        ExpiredMessageRepository, collection=collections.message_collection
    )
    expired_llm_turn_repo: Singleton[ExpiredLlmTurnRepository] = Singleton(
        ExpiredLlmTurnRepository, collection=collections.llm_turn_collection
    )
    expired_missed_call_repo: Singleton[ExpiredMissedCallRepository] = Singleton(
        ExpiredMissedCallRepository, collection=call_adapters.missed_call_collection
    )
    expiring_lead_repo: Singleton[ExpiringLeadRepository] = Singleton(
        ExpiringLeadRepository, collection=collections.lead_collection
    )
    expiring_handoff_repo: Singleton[ExpiringHandoffRepository] = Singleton(
        ExpiringHandoffRepository, collection=collections.handoff_collection
    )
    expiring_booking_repo: Singleton[ExpiringBookingRepository] = Singleton(
        ExpiringBookingRepository, collection=collections.booking_collection
    )
