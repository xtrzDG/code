from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.inbox_collections_container import (
    InboxCollectionsContainer,
)
from app.repositories.assistant_settings_repository import (
    AssistantSettingsRepository,
)
from app.repositories.customer_history_repository import CustomerHistoryRepository
from app.repositories.customer_repositories import (
    CustomerSegmentRepository,
    CustomerSettingsRepository,
)
from app.repositories.inbox_repositories import (
    ConversationNoteRepository,
    InboxSettingsRepository,
    QuickReplyLibraryRepository,
)


class InboxRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the team inbox (migration 1053): internal notes,
    saved replies and the inbox settings. `RepositoriesContainer` extends
    it, so they are read as `repositories.conversation_note_repo` like
    every other repository; `conversation_repo` serves the inbox views and
    assignments, `inbox_work_repo` the open work behind a page. Customers
    (1140): saved segments, the team's customer settings and what customers
    did across channels (`contact_repo` keeps their card).
    """

    inbox_collections: InboxCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    conversation_note_repo: Singleton[ConversationNoteRepository] = Singleton(
        ConversationNoteRepository,
        collection=inbox_collections.conversation_note_collection,
    )
    quick_reply_library_repo: Singleton[QuickReplyLibraryRepository] = Singleton(
        QuickReplyLibraryRepository,
        collection=inbox_collections.quick_reply_library_collection,
    )
    inbox_settings_repo: Singleton[InboxSettingsRepository] = Singleton(
        InboxSettingsRepository,
        collection=inbox_collections.inbox_settings_collection,
    )
    # How the assistant remembers returning customers (1121).
    assistant_settings_repo: Singleton[AssistantSettingsRepository] = Singleton(
        AssistantSettingsRepository,
        collection=inbox_collections.assistant_settings_collection,
    )
    # Customers (1140).
    customer_segment_repo: Singleton[CustomerSegmentRepository] = Singleton(
        CustomerSegmentRepository,
        collection=inbox_collections.customer_segment_collection,
    )
    customer_settings_repo: Singleton[CustomerSettingsRepository] = Singleton(
        CustomerSettingsRepository,
        collection=inbox_collections.customer_settings_collection,
    )
    customer_history_repo: Singleton[CustomerHistoryRepository] = Singleton(
        CustomerHistoryRepository,
        conversation_collection=collections.conversation_collection,
        booking_collection=collections.booking_collection,
        call_collection=collections.call_collection,
    )
