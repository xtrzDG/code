"""
A message repository of a business with a long history, made up on read:
every message is built when a page asks for it, so a test measures what
the export holds, not what the store holds.
"""

import uuid
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText

# A version 4, variant 1 UUID whose low bits carry the message's number.
UUID_V4_BITS: int = (0x4 << 76) | (0x8 << 60)
NUMBER_MASK: int = (1 << 60) - 1
TEXTS: tuple[str, ...] = (
    "გამარჯობა! ხვალ 19:00-ზე ორზე მაგიდა გაქვთ?",
    "Здравствуйте! Можно забронировать столик на четверых в пятницу?",
    "Hello! Do you have vegetarian khinkali, and is there parking nearby?",
)


def message_id(number: int) -> MessageId:
    return MessageId(f"message_{uuid.UUID(int=UUID_V4_BITS | number)}")


def number_of(message_key: str) -> int:
    return uuid.UUID(message_key.removeprefix("message_")).int & NUMBER_MASK


def template(
    business_id: BusinessId,
    conversation_id: ConversationId,
    text: str,
    is_customer: bool,
    at: Microseconds,
) -> MessageDocument:
    return MessageDocument(
        conversation_id=conversation_id,
        business_id=business_id,
        direction=MessageDirection.INBOUND
        if is_customer
        else MessageDirection.OUTBOUND,
        author=MessageAuthor.CUSTOMER if is_customer else MessageAuthor.ASSISTANT,
        text=MessageText(text),
        created_at=at,
        updated_at=at,
    )


class GeneratedMessages:
    """
    `per_conversation` messages in each conversation, in write order: the
    reads of `MessageRepoContract` a full export makes.
    """

    def __init__(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
        per_conversation: int,
        first_at: Microseconds,
    ) -> None:
        self._business_id: BusinessId = business_id
        self._conversation_ids: list[ConversationId] = list(conversation_ids)
        self._index: dict[ConversationId, int] = {
            conversation_id: index
            for index, conversation_id in enumerate(self._conversation_ids)
        }
        self._per_conversation: int = per_conversation
        self._first_at: int = int(first_at)
        self._templates: list[MessageDocument] = [
            template(
                business_id, self._conversation_ids[0], text, is_customer, first_at
            )
            for text in TEXTS
            for is_customer in (True, False)
        ]

    @property
    def count(self) -> int:
        return len(self._conversation_ids) * self._per_conversation

    def message(self, number: int) -> MessageDocument:
        # Copies of six validated templates (validating each of thousands of
        # messages would measure pydantic, not the export).
        at = Microseconds(self._first_at + number * 1_000_000)
        return self._templates[number % len(self._templates)].model_copy(
            update={
                "id": message_id(number),
                "conversation_id": self._conversation_ids[
                    number // self._per_conversation
                ],
                "created_at": at,
                "updated_at": at,
            }
        )

    def page_in_write_order(
        self, business_id: BusinessId, window: KeysetSlice
    ) -> list[MessageDocument]:
        if business_id != self._business_id:
            return []

        start: int = (
            0 if window.after is None else number_of(str(window.after.item_key)) + 1
        )
        end: int = min(self.count, start + int(window.limit))
        return [self.message(number) for number in range(start, end)]

    def list_by_conversations(
        self, business_id: BusinessId, conversation_ids: Sequence[ConversationId]
    ) -> list[MessageDocument]:
        if business_id != self._business_id:
            return []

        return [
            self.message(self._index[conversation_id] * self._per_conversation + offset)
            for conversation_id in conversation_ids
            if conversation_id in self._index
            for offset in range(self._per_conversation)
        ]
