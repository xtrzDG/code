"""
The production quality of a demo business: what the nightly sampling's
judge would have stored for eight of the month's conversations, spread
over the 30 days. One scores below 3 (the conversation the owner rated
bad, else one the assistant could not answer), with the judge's note in
the owner's language; the others score 4 to 5.
"""

from collections.abc import Sequence
from datetime import timedelta

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, JudgeCriterion
from app.schemas.constants.conversations import ConversationRating, MessageAuthor
from app.schemas.domain.assistants import JudgeCriterionScore
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.typings.assistants.constrained_integers import JudgeScore
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.utilities.quality.quality_sampling import quality_score_id_of, to_hundredths

SAMPLED_CONVERSATIONS: int = 8
WINDOW_MICROSECONDS: int = int(timedelta(days=30).total_seconds()) * 1_000_000
# The sampling runs at night: a conversation is judged about 8 hours later.
JUDGED_AFTER_MICROSECONDS: int = int(timedelta(hours=8).total_seconds()) * 1_000_000
JUDGE_COST_MICRO_USD: int = 3_200
CRITERIA: tuple[JudgeCriterion, ...] = tuple(JudgeCriterion)
# Scores of the criteria in CRITERIA's order.
GOOD_SCORES: tuple[tuple[int, ...], ...] = (
    (5, 5, 5, 5, 5),
    (5, 4, 5, 5, 5),
    (4, 5, 5, 4, 5),
    (5, 5, 4, 5, 5),
)
LOW_SCORES: tuple[int, ...] = (2, 3, 4, 2, 3)
LOW_NOTES: dict[str, tuple[str, ...]] = {
    "ru": (
        "Ответа на вопрос клиента в данных бизнеса нет: помощник честно "
        "передал вопрос, но клиент остался без ответа.",
        "Передача сотруднику без срока ответа.",
    ),
    "de": (
        "Die Antwort auf die Frage des Kunden fehlt in den Angaben des "
        "Geschäfts: Der Assistent hat sie weitergegeben, der Kunde blieb "
        "ohne Antwort.",
        "Übergabe an das Team ohne Zeitangabe.",
    ),
    "en": (
        "The business's details have no answer to the customer's question: "
        "the assistant passed it on, and the customer was left without one.",
        "Handed to staff without saying when they would reply.",
    ),
}


def build_demo_quality_scores(
    business: BusinessDocument,
    conversations: Sequence[ConversationDocument],
    messages: Sequence[MessageDocument],
    judge_model_id: LlmModelId,
    now: Microseconds,
) -> list[ConversationQualityScoreDocument]:
    """Eight judged conversations of the last 30 days, oldest first."""

    answered: set[ConversationId] = {
        message.conversation_id
        for message in messages
        if message.author is MessageAuthor.ASSISTANT
    }
    candidates: list[ConversationDocument] = sorted(
        (
            conversation
            for conversation in conversations
            if not conversation.is_sandbox
            and conversation.id in answered
            and int(conversation.created_at) >= int(now) - WINDOW_MICROSECONDS
            and judged_at(conversation) <= int(now)
        ),
        key=lambda conversation: int(conversation.created_at),
    )
    if not candidates:
        return []

    low: ConversationDocument = weakest(candidates, messages)
    others: list[ConversationDocument] = [
        conversation for conversation in candidates if conversation.id != low.id
    ]
    step: float = max(len(others) / (SAMPLED_CONVERSATIONS - 1), 1.0)
    picked: list[ConversationDocument] = [
        others[int(position * step)]
        for position in range(min(SAMPLED_CONVERSATIONS - 1, len(others)))
    ]
    return [
        judged(
            business,
            conversation,
            LOW_SCORES if conversation.id == low.id else GOOD_SCORES[index % 4],
            conversation.id == low.id,
            judge_model_id,
        )
        for index, conversation in enumerate(
            sorted([*picked, low], key=lambda item: int(item.created_at))
        )
    ]


def judged_at(conversation: ConversationDocument) -> int:
    return int(conversation.last_message_at) + JUDGED_AFTER_MICROSECONDS


def weakest(
    candidates: Sequence[ConversationDocument], messages: Sequence[MessageDocument]
) -> ConversationDocument:
    """
    The conversation the owner rated bad, else one with a question the
    assistant could not answer, else the first.
    """

    unanswered: set[ConversationId] = {
        message.conversation_id
        for message in messages
        if any(
            call.tool_name is AssistantToolName.RECORD_UNANSWERED_QUESTION
            for call in message.tool_calls
        )
    }
    return next(
        (item for item in candidates if item.rating is ConversationRating.BAD),
        next((item for item in candidates if item.id in unanswered), candidates[0]),
    )


def judged(
    business: BusinessDocument,
    conversation: ConversationDocument,
    scores: tuple[int, ...],
    is_low: bool,
    judge_model_id: LlmModelId,
) -> ConversationQualityScoreDocument:
    criteria: list[JudgeCriterionScore] = [
        JudgeCriterionScore(criterion=criterion, score=JudgeScore(score))
        for criterion, score in zip(CRITERIA, scores, strict=True)
    ]
    moment: Microseconds = Microseconds(judged_at(conversation))
    language: str = str(business.owner_language).split("-")[0]
    return ConversationQualityScoreDocument(
        id=quality_score_id_of(conversation.id),
        business_id=business.id,
        conversation_id=conversation.id,
        assistant_version_id=conversation.assistant_version_id,
        channel=conversation.channel,
        language=conversation.language,
        scores=criteria,
        score_hundredths=to_hundredths(criteria),
        judge_notes=(
            [JudgeNote(note) for note in LOW_NOTES.get(language, LOW_NOTES["en"])]
            if is_low
            else []
        ),
        judge_model_id=judge_model_id,
        cost_micro_usd=CostMicroUsd(JUDGE_COST_MICRO_USD),
        judged_at=moment,
        created_at=moment,
        updated_at=moment,
    )
