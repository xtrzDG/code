from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.call_adapters_container import CallAdaptersContainer
from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
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


class RetentionRepositoriesContainer(containers.DeclarativeContainer):
    """
    The retention purge's reads and batched deletes over the conversation,
    booking and call collections (1123; the privacy settings and purge
    state are PrivacyRepositoriesContainer's). `RepositoriesContainer`
    extends it, so they are read as `repositories.expired_message_repo`
    like every other repository. Its edges have their own names, so they
    never shadow the bases' edges to the same containers.
    """

    retention_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    retention_call_adapters: CallAdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    quiet_conversation_repo: Singleton[QuietConversationRepository] = Singleton(
        QuietConversationRepository,
        collection=retention_collections.conversation_collection,
    )
    expired_message_repo: Singleton[ExpiredMessageRepository] = Singleton(
        ExpiredMessageRepository, collection=retention_collections.message_collection
    )
    expired_llm_turn_repo: Singleton[ExpiredLlmTurnRepository] = Singleton(
        ExpiredLlmTurnRepository, collection=retention_collections.llm_turn_collection
    )
    expired_missed_call_repo: Singleton[ExpiredMissedCallRepository] = Singleton(
        ExpiredMissedCallRepository,
        collection=retention_call_adapters.missed_call_collection,
    )
    expiring_lead_repo: Singleton[ExpiringLeadRepository] = Singleton(
        ExpiringLeadRepository, collection=retention_collections.lead_collection
    )
    expiring_handoff_repo: Singleton[ExpiringHandoffRepository] = Singleton(
        ExpiringHandoffRepository, collection=retention_collections.handoff_collection
    )
    expiring_booking_repo: Singleton[ExpiringBookingRepository] = Singleton(
        ExpiringBookingRepository, collection=retention_collections.booking_collection
    )
