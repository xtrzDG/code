from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.value_collections_container import (
    ValueCollectionsContainer,
)
from app.repositories.customer_source_repository import CustomerSourceRepository
from app.repositories.quality_repositories import (
    ConversationQualityRepository,
    QualitySampleInputRepository,
    QualityTotalsRepository,
)
from app.repositories.topic_repositories import (
    ConversationTopicsRepository,
    TopicInputRepository,
)
from app.repositories.value_repositories import (
    DigestPreferencesRepository,
    ValueReportRepository,
    ValueSettingsRepository,
)


class ValueRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of what the assistant is worth (migration 1061): the
    average check, each owner's digest choices and the stored reports; and
    where customers came from and what they ask about (1100); and how good
    the assistant's real conversations are (production quality, 1120).
    `RepositoriesContainer` extends it, so they are read as
    `repositories.value_report_repo` like every other repository; the
    counts the value model adds to the dashboard's are `value_count_repo`.
    """

    value_collections: ValueCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    # The conversations, messages, bookings and requests the sources and
    # topics are read from.
    insight_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    value_settings_repo: Singleton[ValueSettingsRepository] = Singleton(
        ValueSettingsRepository,
        collection=value_collections.value_settings_collection,
    )
    digest_preferences_repo: Singleton[DigestPreferencesRepository] = Singleton(
        DigestPreferencesRepository,
        collection=value_collections.digest_preferences_collection,
    )
    value_report_repo: Singleton[ValueReportRepository] = Singleton(
        ValueReportRepository,
        collection=value_collections.value_report_collection,
    )
    conversation_topics_repo: Singleton[ConversationTopicsRepository] = Singleton(
        ConversationTopicsRepository,
        collection=value_collections.conversation_topics_collection,
    )
    topic_input_repo: Singleton[TopicInputRepository] = Singleton(
        TopicInputRepository,
        conversation_collection=insight_collections.conversation_collection,
        message_collection=insight_collections.message_collection,
    )
    customer_source_repo: Singleton[CustomerSourceRepository] = Singleton(
        CustomerSourceRepository,
        conversation_collection=insight_collections.conversation_collection,
        booking_collection=insight_collections.booking_collection,
        lead_collection=insight_collections.lead_collection,
    )
    conversation_quality_repo: Singleton[ConversationQualityRepository] = Singleton(
        ConversationQualityRepository,
        collection=value_collections.conversation_quality_collection,
    )
    quality_totals_repo: Singleton[QualityTotalsRepository] = Singleton(
        QualityTotalsRepository,
        collection=value_collections.conversation_quality_collection,
    )
    quality_sample_input_repo: Singleton[QualitySampleInputRepository] = Singleton(
        QualitySampleInputRepository,
        conversation_collection=insight_collections.conversation_collection,
    )
