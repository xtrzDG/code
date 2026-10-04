"""
The review fields of a conversation: the owner's or staff's rating, why
it was bad, the answer it is about and whether someone acted on it. Only
their own writes change them (`ConversationReviewRepoContract`); a plain
save of the conversation keeps what is stored, so a customer turn that
read the conversation before it was rated cannot undo the rating.
"""

from app.schemas.constants.conversations import ConversationRating
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.conversations.booleans import AwaitsImprovement

REVIEW_OWNED_FIELDS: tuple[str, ...] = (
    "rating",
    "rated_by",
    "rated_at",
    "rating_reason",
    "rated_message_id",
    "improved_at",
    "awaits_improvement",
)


def awaits_improvement(conversation: ConversationDocument) -> AwaitsImprovement:
    """
    Rated bad, not a test conversation, and nobody corrected an answer or
    saved a check from it since it was rated.
    """

    if conversation.rating is not ConversationRating.BAD or conversation.is_sandbox:
        return False

    if conversation.improved_at is None or conversation.rated_at is None:
        return True

    return int(conversation.improved_at) < int(conversation.rated_at)


def with_review_attention(conversation: ConversationDocument) -> ConversationDocument:
    """The conversation with `awaits_improvement` derived from its review."""

    derived: AwaitsImprovement = awaits_improvement(conversation)
    if conversation.awaits_improvement == derived:
        return conversation

    return conversation.model_copy(update={"awaits_improvement": derived})
