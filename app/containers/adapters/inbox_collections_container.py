from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument


class InboxCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the team inbox (migration 1053): internal
    notes on conversations, each business's saved replies and its
    auto-assignment settings; and how the assistant remembers returning
    customers (migration 1121); Customers' saved segments and settings
    (1140). A sibling of DocumentCollectionsContainer
    with the same storage factory (Postgres with DATABASE_URL, else in
    memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    conversation_note_collection = document_collection(
        ConversationNoteDocument,
        "conversation_notes",
        config,
        clients,
        utilities,
        time_provider,
    )
    quick_reply_library_collection = document_collection(
        QuickReplyLibraryDocument,
        "quick_reply_libraries",
        config,
        clients,
        utilities,
        time_provider,
    )
    inbox_settings_collection = document_collection(
        InboxSettingsDocument,
        "inbox_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    # How the assistant remembers returning customers (1121).
    assistant_settings_collection = document_collection(
        AssistantSettingsDocument,
        "assistant_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    # Customers: saved segments and the team's customer settings (1140).
    customer_segment_collection = document_collection(
        CustomerSegmentDocument,
        "customer_segments",
        config,
        clients,
        utilities,
        time_provider,
    )
    customer_settings_collection = document_collection(
        CustomerSettingsDocument,
        "customer_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
