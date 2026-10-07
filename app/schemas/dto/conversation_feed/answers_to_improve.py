"""The Overview's "Answers worth improving": questions without an answer and
conversations rated bad that nobody acted on yet."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.conversations import (
    AnswerToImproveKind,
    ConversationRatingReason,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    AnswersToImproveLimit,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessagePreview
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.users.prefixed_id import UserId

DEFAULT_ANSWERS_TO_IMPROVE: AnswersToImproveLimit = AnswersToImproveLimit(5)


class AnswersToImproveQuery(ImmutableDTO):
    """An owner or staff member opens the Overview."""

    user_id: UserId
    business_id: BusinessId
    limit: AnswersToImproveLimit = DEFAULT_ANSWERS_TO_IMPROVE


class AnswerToImproveView(ImmutableDTO):
    """
    One answer worth improving. A question the assistant could not answer
    (UNANSWERED_QUESTION) has its `question_id`, `question`, how often it
    was asked and its language; a conversation rated bad (BAD_RATING) its
    `conversation_id`, the rated answer (`message_id`, `answer`), the
    customer's last words (`customer_message`) and the reason given.
    `at` is when it was last asked or written.
    """

    kind: AnswerToImproveKind
    question_id: UnansweredQuestionId | None = None
    question: UnansweredQuestionText | None = None
    occurrence_count: QuestionOccurrenceCount | None = None
    conversation_id: ConversationId | None = None
    message_id: MessageId | None = None
    customer_message: MessagePreview | None = None
    answer: MessagePreview | None = None
    rating_reason: ConversationRatingReason | None = None
    language: LanguageTag | None = None
    at: Microseconds


class AnswersToImproveView(ImmutableDTO):
    """
    The bad ratings first (newest first), then the questions without an
    answer (most asked first), at most `limit` together, and how many of
    each wait in all.
    """

    items: list[AnswerToImproveView] = Field(default_factory=list[AnswerToImproveView])
    bad_rating_count: ListItemCount
    unanswered_count: ListItemCount
