from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
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
        for contact in self._list(business_id):
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
        for contact in self._list(business_id):
            if contact.phone_number == phone_number:
                return contact

        return None

    def find_by_verified_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        for contact in self._list(business_id):
            if contact.verified_phone_number == phone_number:
                return contact

        return None

    def list_by_business(self, business_id: BusinessId) -> list[ContactDocument]:
        return self._list(business_id)

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
        return sorted(
            self._list(business_id),
            key=lambda conversation: conversation.last_message_at,
            reverse=True,
        )

    def list_by_channel_user(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> list[ConversationDocument]:
        return sorted(
            (
                conversation
                for conversation in self._list_by_field(
                    business_id, "channel_user_id", str(channel_user_id)
                )
                if conversation.channel is channel
            ),
            key=lambda conversation: conversation.last_message_at,
            reverse=True,
        )


class MessageRepository(
    BusinessScopedRepository[MessageDocument],
    MessageRepoContract,
):
    def save(self, message: MessageDocument) -> None:
        self._store(str(message.id), message)

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[MessageDocument]:
        messages: list[MessageDocument] = [
            message
            for message in self._list_by_field(
                business_id, "conversation_id", str(conversation_id)
            )
            if message.conversation_id == conversation_id
        ]
        return sorted(messages, key=lambda message: message.created_at)

    def list_by_business(self, business_id: BusinessId) -> list[MessageDocument]:
        return sorted(self._list(business_id), key=lambda message: message.created_at)

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
        turns: list[LlmTurnDocument] = [
            turn
            for turn in self._collection.list_all()
            if turn.conversation_id == conversation_id
        ]
        return sorted(turns, key=lambda turn: turn.sequence_number)

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
        for call in self._list(business_id):
            if call.provider_call_id == provider_call_id:
                return call

        return None

    def list_by_business(self, business_id: BusinessId) -> list[CallDocument]:
        return sorted(
            self._list(business_id),
            key=lambda call: call.started_at,
            reverse=True,
        )
