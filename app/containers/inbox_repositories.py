from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.inbox_collections_container import (
    InboxCollectionsContainer,
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
    assignments, `inbox_work_repo` the open work behind a page.
    """

    inbox_collections: InboxCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

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
