"""
The assistant answer an owner fixes, its conversation, and the customer
message it answered.
"""

from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey

# How far back the question of an answer is looked for: a few messages
# (a customer's burst, a tool note, a staff line) before the answer.
QUESTION_LOOKBACK: KeysetReadLimit = KeysetReadLimit(8)


def load_answer(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business_id: BusinessId,
    conversation_id: ConversationId,
    message_id: MessageId,
) -> tuple[ConversationDocument, MessageDocument]:
    """
    The conversation and its assistant message.

    Raises:
        NotFoundError: the conversation or the message is missing, or the
            message belongs to another conversation.
        ValidationFailedError: the message is not the assistant's.
    """

    conversation: ConversationDocument | None = conversation_repo.get(
        business_id, conversation_id
    )
    if conversation is None:
        raise NotFoundError(f"Conversation {conversation_id} was not found.")

    message: MessageDocument | None = message_repo.get(business_id, message_id)
    if message is None or message.conversation_id != conversation.id:
        raise NotFoundError(f"Message {message_id} was not found.")

    if message.author is not MessageAuthor.ASSISTANT:
        raise ValidationFailedError("Only an answer of the assistant can be fixed.")

    return conversation, message


def find_question(
    message_repo: MessageRepoContract,
    business_id: BusinessId,
    answer: MessageDocument,
) -> MessageDocument | None:
    """
    The latest customer message with words before the answer (None when
    the answer opened the conversation), one indexed read.
    """

    earlier: list[MessageDocument] = message_repo.page_transcript(
        business_id,
        answer.conversation_id,
        KeysetSlice(
            after=KeysetPosition(
                sort_values=(ListSortValue(int(answer.created_at)),),
                item_key=ListItemKey(str(answer.id)),
            ),
            limit=QUESTION_LOOKBACK,
        ),
    )
    for message in earlier:
        if message.author is MessageAuthor.CUSTOMER and str(message.text).strip():
            return message

    return None
