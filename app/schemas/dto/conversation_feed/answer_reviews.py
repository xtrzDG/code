"""
The review of an assistant answer: a rating with its reason, and the
mark that someone acted on a bad one (corrected the answer or saved a
check from it).
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.conversations import (
    ConversationRating,
    ConversationRatingReason,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.users.prefixed_id import UserId


class ConversationRatingChange(ImmutableDTO):
    """
    A new rating of a conversation (None clears it, with its reason and
    answer): who gave it, when, why it was bad and the answer it is about.
    """

    rating: ConversationRating | None
    rated_by: UserId
    rating_reason: ConversationRatingReason | None = None
    rated_message_id: MessageId | None = None
    at: Microseconds
