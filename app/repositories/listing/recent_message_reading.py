"""The newest messages of a few conversations together (widget polls)."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    CONVERSATION_ID_FIELD,
    CREATED_AT_FIELD,
)
from app.repositories.document_queries import field_among, field_equals
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_pages import DocumentPagePosition
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId


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

        where: DocumentFilter | None = of_conversations(conversation_ids)
        if where is None:
            return []

        return self._page_in_business(
            business_id, (CREATED_AT_FIELD,), window, where, is_descending=True
        )

    def page_newest_positions_of_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
        window: KeysetSlice,
    ) -> list[MessagePosition]:
        """
        Where the messages `page_newest_of_conversations` returns stand, in
        the same order, read from the index columns without the messages.
        """

        where: DocumentFilter | None = of_conversations(conversation_ids)
        if where is None:
            return []

        return [
            read_message_position(position)
            for position in self._page_positions_in_business(
                business_id, (CREATED_AT_FIELD,), window, where, is_descending=True
            )
        ]


def of_conversations(
    conversation_ids: Sequence[ConversationId],
) -> DocumentFilter | None:
    """Messages of any of these conversations; None for none."""

    unique_ids: list[ConversationId] = list(dict.fromkeys(conversation_ids))
    if not unique_ids:
        return None

    if len(unique_ids) == 1:
        return DocumentFilter(
            matches=(field_equals(CONVERSATION_ID_FIELD, unique_ids[0]),)
        )

    return DocumentFilter(among=(field_among(CONVERSATION_ID_FIELD, unique_ids),))


def read_message_position(position: DocumentPagePosition) -> MessagePosition:
    """A page position by `created_at` of a message (its key is its id)."""

    return MessagePosition(
        id=MessageId(str(position.document_key)),
        created_at=Microseconds(int(position.values[0])),
    )
