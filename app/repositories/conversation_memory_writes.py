"""
The customer memory side of `ConversationRepository`: a customer's latest
conversations and how many they had (the (business_id, contact_id,
last_message_at) index of 1010), and their summaries, written in one step
each.
"""

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    CONTACT_ID_FIELD,
    LAST_MESSAGE_AT_FIELD,
)
from app.repositories.document_queries import (
    IS_SANDBOX_FIELD,
    descending,
    field_equals,
)
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.customer_memory.conversation_summaries import (
    ConversationSummaryWrite,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.privacy.erased_conversations import is_erased_conversation


class ConversationMemoryWrites(BusinessScopedRepository[ConversationDocument]):
    """A customer's conversations as the assistant remembers them."""

    def list_latest_by_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(CONTACT_ID_FIELD, contact_id)],
            order=descending(LAST_MESSAGE_AT_FIELD),
            limit=limit,
        )

    def count_by_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> ListItemCount:
        return ListItemCount(
            int(
                self._count_in_business(
                    business_id,
                    [
                        field_equals(CONTACT_ID_FIELD, contact_id),
                        field_equals(IS_SANDBOX_FIELD, False),
                    ],
                )
            )
        )

    def set_summary(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        write: ConversationSummaryWrite,
    ) -> ConversationDocument | None:
        def summarize(stored: ConversationDocument) -> ConversationDocument | None:
            if stored.last_message_at != write.covers_until or is_erased_conversation(
                stored
            ):
                return None

            return stored.model_copy(
                update={
                    "summary": write.summary,
                    "summarized_at": write.written_at,
                    "updated_at": write.written_at,
                }
            )

        return self._modify_in_business(business_id, str(conversation_id), summarize)
