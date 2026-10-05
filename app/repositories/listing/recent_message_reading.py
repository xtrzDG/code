"""The newest messages of a few conversations together (widget polls)."""

from collections.abc import Sequence

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    CONVERSATION_ID_FIELD,
    CREATED_AT_FIELD,
)
from app.repositories.document_queries import field_among, field_equals
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId


class RecentMessageReading(BusinessScopedRepository[MessageDocument]):
    """One keyset page of the newest messages of several conversations."""

    def page_newest_of_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
        window: KeysetSlice,
    ) -> list[MessageDocument]:
        """
        Newest first. One conversation (a widget visitor's usual case) is
        an equality on the (business, conversation, created_at) index, so
        the page reads only its own rows backwards from the newest; several
        are one `any(...)` probe of the same index.
        """

        unique_ids: list[ConversationId] = list(dict.fromkeys(conversation_ids))
        if not unique_ids:
            return []

        where: DocumentFilter = (
            DocumentFilter(
                matches=(field_equals(CONVERSATION_ID_FIELD, unique_ids[0]),)
            )
            if len(unique_ids) == 1
            else DocumentFilter(among=(field_among(CONVERSATION_ID_FIELD, unique_ids),))
        )
        return self._page_in_business(
            business_id, (CREATED_AT_FIELD,), window, where, is_descending=True
        )
