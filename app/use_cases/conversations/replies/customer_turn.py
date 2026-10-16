"""The user turn of one customer message, as the model reads it."""

from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.media import LlmImageInput, MediaLocation
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.use_cases.conversations.replies.reply_evidence import (
    collect_unanswered_messages,
)
from app.utilities.conversations.message_context_notes import (
    describe_context_note,
)
from app.utilities.conversations.turn_context import (
    build_text_with_unanswered_messages,
    build_user_turn_text,
)
from app.utilities.media.attachment_texts import is_readable


def build_customer_turn(
    llm_adapter: LlmAdapterContract,
    message_repo: MessageRepoContract,
    turn: PreparedTurn,
    stored_turns: list[LlmTurnDocument],
    fence_key: str,
) -> LlmProviderPayload:
    """
    The context line (and what the message refers to, such as a reply to
    the business's Instagram story), the messages the assistant stayed
    silent on, then this message as the model reads it (fenced, with a line
    per attachment) and its photos as pictures.
    """

    context: str = str(turn.context_line)
    if turn.context_note is not None:
        context = f"{context}\n{describe_context_note(turn.context_note)}"

    text = MessageText(
        build_user_turn_text(
            context,
            build_text_with_unanswered_messages(
                collect_unanswered_messages(message_repo, turn, stored_turns),
                str(turn.model_text),
                fence_key,
            ),
            fence_key,
        )
    )
    images: list[LlmImageInput] = turn_photos(turn)
    if not images:
        return llm_adapter.build_user_text_turn(text)

    return llm_adapter.build_user_media_turn(text, images)


def turn_photos(turn: PreparedTurn) -> list[LlmImageInput]:
    """The stored photos of the message the model can be shown."""

    return [
        LlmImageInput(
            location=MediaLocation(
                business_id=turn.business.id, path=attachment.storage_path
            ),
            media_type=attachment.media_type,
        )
        for attachment in turn.attachments
        if attachment.kind is AttachmentKind.IMAGE
        and is_readable(attachment)
        and attachment.storage_path is not None
        and attachment.media_type is not None
    ]
