from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    ConversationMessageRepoContract,
    ConversationRepoContract,
    LlmTurnRepoContract,
)
from app.schemas.domain.conversations import (
    ConversationDocument,
    ConversationMessageDocument,
    LlmTurnDocument,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId


class ConversationRepository(ConversationRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ConversationDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[ConversationDocument] = (
            collection
        )

    def save(self, conversation: ConversationDocument) -> None:
        self._collection.upsert(str(conversation.id), conversation)

    def get(self, conversation_id: ConversationId) -> ConversationDocument | None:
        return self._collection.get(str(conversation_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationDocument]:
        conversations: list[ConversationDocument] = [
            conversation
            for conversation in self._collection.list_all()
            if conversation.business_id == business_id
        ]
        return sorted(
            conversations,
            key=lambda conversation: conversation.last_message_at,
            reverse=True,
        )


class ConversationMessageRepository(ConversationMessageRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ConversationMessageDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            ConversationMessageDocument
        ] = collection

    def save(self, message: ConversationMessageDocument) -> None:
        self._collection.upsert(str(message.id), message)

    def list_by_conversation(
        self,
        conversation_id: ConversationId,
    ) -> list[ConversationMessageDocument]:
        messages: list[ConversationMessageDocument] = [
            message
            for message in self._collection.list_all()
            if message.conversation_id == conversation_id
        ]
        return sorted(messages, key=lambda message: message.created_at)

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ConversationMessageDocument]:
        messages: list[ConversationMessageDocument] = [
            message
            for message in self._collection.list_all()
            if message.business_id == business_id
        ]
        return sorted(messages, key=lambda message: message.created_at)


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
