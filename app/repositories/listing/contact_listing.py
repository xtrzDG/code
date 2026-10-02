"""Several contacts in one read, and the calls of one conversation."""

from collections.abc import Sequence

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import CONVERSATION_ID_FIELD
from app.repositories.document_queries import field_equals
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId


class ContactListing(BusinessScopedRepository[ContactDocument]):
    """The contacts a page of a list names, read together."""

    def get_many(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
    ) -> dict[ContactId, ContactDocument]:
        return {
            contact.id: contact
            for contact in self._load_many(
                business_id, [str(contact_id) for contact_id in contact_ids]
            )
        }


class CallListing(BusinessScopedRepository[CallDocument]):
    """The calls of one conversation (its card), the earliest first."""

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[CallDocument]:
        return sorted(
            self._list_in_business(
                business_id, [field_equals(CONVERSATION_ID_FIELD, conversation_id)]
            ),
            key=lambda call: int(call.started_at),
        )
