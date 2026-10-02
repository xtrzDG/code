from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    AUTHOR_FIELD,
    CHANNEL_USER_ID_FIELD,
    CHANNEL_USER_IDS_FIELD,
    CONTACT_ID_FIELD,
    CONVERSATION_ID_FIELD,
    CREATED_AT_FIELD,
    DIRECTION_FIELD,
    LAST_MESSAGE_AT_FIELD,
    PHONE_NUMBER_FIELD,
    PROVIDER_CALL_ID_FIELD,
    SEQUENCE_NUMBER_FIELD,
    STATUS_FIELD,
    VERIFIED_PHONE_NUMBER_FIELD,
)
from app.repositories.document_queries import (
    ascending,
    descending,
    field_equals,
    time_range,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFieldRange
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
)
from app.schemas.typings.conversations.prefixed_id import (
    CallId,
    ConversationId,
    MessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class ContactRepository(
    BusinessScopedRepository[ContactDocument],
    ContactRepoContract,
):
    def save(self, contact: ContactDocument) -> None:
        self._store(str(contact.id), contact)

    def get(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> ContactDocument | None:
        return self._load(business_id, str(contact_id))

    def find_by_channel_identity(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> ContactDocument | None:
        # Indexed by the user id; the channel is checked on the few found.
        for contact in self._list_in_business(
            business_id, [field_equals(CHANNEL_USER_IDS_FIELD, channel_user_id)]
        ):
            for identity in contact.channel_identities:
                if (
                    identity.channel is channel
                    and identity.channel_user_id == channel_user_id
                ):
                    return contact

        return None

    def find_by_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        return self._find_in_business(
            business_id, [field_equals(PHONE_NUMBER_FIELD, phone_number)]
        )

    def find_by_verified_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        return self._find_in_business(
            business_id, [field_equals(VERIFIED_PHONE_NUMBER_FIELD, phone_number)]
        )

    def list_by_business(self, business_id: BusinessId) -> list[ContactDocument]:
        return self._list_in_business(business_id)

    def delete(self, business_id: BusinessId, contact_id: ContactId) -> None:
        self._remove(business_id, str(contact_id))


class ConversationRepository(
    BusinessScopedRepository[ConversationDocument],
    ConversationRepoContract,
):
    def save(self, conversation: ConversationDocument) -> None:
        self._store(str(conversation.id), conversation)

    def get(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationDocument | None:
        return self._load(business_id, str(conversation_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationDocument]:
        return self._list_in_business(
            business_id, order=descending(LAST_MESSAGE_AT_FIELD)
        )

    def list_by_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
        last_message_from: Microseconds | None = None,
        status: ConversationStatus | None = None,
    ) -> list[ConversationDocument]:
        matches: list[DocumentFieldMatch] = [field_equals(CONTACT_ID_FIELD, contact_id)]
        if status is not None:
            matches.append(field_equals(STATUS_FIELD, status))

        if last_message_from is None:
            return self._list_in_business(
                business_id, matches, order=descending(LAST_MESSAGE_AT_FIELD)
            )

        return self._list_in_range(
            business_id,
            time_range(LAST_MESSAGE_AT_FIELD, starting_at=last_message_from),
            matches,
            is_descending=True,
        )

    def list_by_channel_user(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> list[ConversationDocument]:
        return [
            conversation
            for conversation in self._list_in_business(
                business_id,
                [field_equals(CHANNEL_USER_ID_FIELD, channel_user_id)],
                order=descending(LAST_MESSAGE_AT_FIELD),
            )
            if conversation.channel is channel
        ]


class MessageRepository(
    BusinessScopedRepository[MessageDocument],
    MessageRepoContract,
):
    def save(self, message: MessageDocument) -> None:
        self._store(str(message.id), message)

    def get(
        self,
        business_id: BusinessId,
        message_id: MessageId,
    ) -> MessageDocument | None:
        return self._load(business_id, str(message_id))

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[MessageDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(CONVERSATION_ID_FIELD, conversation_id)],
            order=ascending(CREATED_AT_FIELD),
        )

    def count_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        direction: MessageDirection,
        author: MessageAuthor | None = None,
        created_from: Microseconds | None = None,
    ) -> ConversationMessageCount:
        matches: list[DocumentFieldMatch] = [
            field_equals(CONVERSATION_ID_FIELD, conversation_id),
            field_equals(DIRECTION_FIELD, direction),
        ]
        if author is not None:
            matches.append(field_equals(AUTHOR_FIELD, author))

        within: DocumentFieldRange | None = (
            None
            if created_from is None
            else time_range(CREATED_AT_FIELD, starting_at=created_from)
        )
        return ConversationMessageCount(
            int(self._count_in_business(business_id, matches, within))
        )

    def list_by_business(self, business_id: BusinessId) -> list[MessageDocument]:
        return self._list_in_business(business_id, order=ascending(CREATED_AT_FIELD))

    def delete_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> None:
        for message in self.list_by_conversation(business_id, conversation_id):
            self._remove(business_id, str(message.id))


class LlmTurnRepository(LlmTurnRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[LlmTurnDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[LlmTurnDocument] = (
            collection
        )

    def append(self, turn: LlmTurnDocument) -> None:
        if self._collection.get(str(turn.id)) is not None:
            raise ConflictError(f"LLM turn {turn.id} is already stored.")

        self._collection.upsert(str(turn.id), turn)

    def list_by_conversation(
        self,
        conversation_id: ConversationId,
    ) -> list[LlmTurnDocument]:
        return self._collection.list_by_fields(
            [field_equals(CONVERSATION_ID_FIELD, conversation_id)],
            order=ascending(SEQUENCE_NUMBER_FIELD),
        )

    def delete_by_conversation(self, conversation_id: ConversationId) -> None:
        for turn in self.list_by_conversation(conversation_id):
            self._collection.delete(str(turn.id))


class CallRepository(BusinessScopedRepository[CallDocument], CallRepoContract):
    def save(self, call: CallDocument) -> None:
        self._store(str(call.id), call)

    def get(self, business_id: BusinessId, call_id: CallId) -> CallDocument | None:
        return self._load(business_id, str(call_id))

    def find_by_provider_call_id(
        self,
        business_id: BusinessId,
        provider_call_id: ProviderCallId,
    ) -> CallDocument | None:
        return self._find_in_business(
            business_id, [field_equals(PROVIDER_CALL_ID_FIELD, provider_call_id)]
        )

    def list_by_business(self, business_id: BusinessId) -> list[CallDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda call: call.started_at,
            reverse=True,
        )
