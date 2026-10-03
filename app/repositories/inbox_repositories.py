"""
Repositories of the team inbox: internal notes, the saved replies and the
inbox settings of each business.
"""

from collections.abc import Callable, Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
    InboxSettingsRepoContract,
    QuickReplyLibraryRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import CONVERSATION_ID_FIELD
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    ascending,
    field_among,
    field_equals,
)
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.constrained_integers import ConversationNoteCount
from app.schemas.typings.inbox.prefixed_id import ConversationNoteId
from app.utilities.inbox.inbox_keys import (
    derive_inbox_settings_id,
    derive_quick_reply_library_id,
)


class ConversationNoteRepository(
    BusinessScopedRepository[ConversationNoteDocument],
    ConversationNoteRepoContract,
):
    """Notes by conversation, newest first (index of migration 1053)."""

    def add(self, note: ConversationNoteDocument) -> None:
        self._store(str(note.id), note)

    def get(
        self,
        business_id: BusinessId,
        note_id: ConversationNoteId,
    ) -> ConversationNoteDocument | None:
        return self._load(business_id, str(note_id))

    def page_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        window: KeysetSlice,
    ) -> list[ConversationNoteDocument]:
        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            DocumentFilter(
                matches=(field_equals(CONVERSATION_ID_FIELD, conversation_id),)
            ),
        )

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[ConversationNoteDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(CONVERSATION_ID_FIELD, conversation_id)],
            order=ascending(CREATED_AT_FIELD),
        )

    def count_by_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, ConversationNoteCount]:
        if not conversation_ids:
            return {}

        groups = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    among=(field_among(CONVERSATION_ID_FIELD, conversation_ids),)
                ),
                group_by=(CONVERSATION_ID_FIELD,),
            ),
        )
        return {
            ConversationId(str(conversation_id)): ConversationNoteCount(
                int(group.count)
            )
            for group in groups
            if (conversation_id := group.values[0]) is not None
        }

    def delete(self, business_id: BusinessId, note_id: ConversationNoteId) -> None:
        self._remove(business_id, str(note_id))

    def delete_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationNoteCount:
        notes = self.list_by_conversation(business_id, conversation_id)
        for note in notes:
            self._collection.delete(str(note.id))

        return ConversationNoteCount(len(notes))


class QuickReplyLibraryRepository(
    BusinessScopedRepository[QuickReplyLibraryDocument],
    QuickReplyLibraryRepoContract,
):
    """One library per business, keyed by its derived id."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> QuickReplyLibraryDocument | None:
        return self._load(business_id, str(derive_quick_reply_library_id(business_id)))

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[QuickReplyLibraryDocument], None],
        now: Microseconds,
    ) -> QuickReplyLibraryDocument:
        library_id = derive_quick_reply_library_id(business_id)
        self._collection.insert_if_absent(
            str(library_id),
            QuickReplyLibraryDocument(
                id=library_id, business_id=business_id, created_at=now, updated_at=now
            ),
        )

        def change_library(
            stored: QuickReplyLibraryDocument,
        ) -> QuickReplyLibraryDocument:
            apply(stored)
            stored.updated_at = now
            return stored

        changed: QuickReplyLibraryDocument | None = self._modify_in_business(
            business_id, str(library_id), change_library
        )
        if changed is None:
            raise NotFoundError(
                f"The saved replies of business {business_id} are gone."
            )

        return changed


class InboxSettingsRepository(
    BusinessScopedRepository[InboxSettingsDocument],
    InboxSettingsRepoContract,
):
    """One settings document per business, keyed by its derived id."""

    def get_by_business(self, business_id: BusinessId) -> InboxSettingsDocument | None:
        return self._load(business_id, str(derive_inbox_settings_id(business_id)))

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[InboxSettingsDocument], None],
        now: Microseconds,
    ) -> InboxSettingsDocument:
        settings_id = derive_inbox_settings_id(business_id)
        self._collection.insert_if_absent(
            str(settings_id),
            InboxSettingsDocument(
                id=settings_id, business_id=business_id, created_at=now, updated_at=now
            ),
        )

        def change_settings(stored: InboxSettingsDocument) -> InboxSettingsDocument:
            apply(stored)
            stored.updated_at = now
            return stored

        changed: InboxSettingsDocument | None = self._modify_in_business(
            business_id, str(settings_id), change_settings
        )
        if changed is None:
            raise NotFoundError(
                f"The inbox settings of business {business_id} are gone."
            )

        return changed
