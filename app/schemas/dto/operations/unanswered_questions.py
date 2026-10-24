"""Unanswered questions in the cabinet: the list and answering a question."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.handoffs.booleans import (
    IsResolvedIncluded,
    IsUnansweredQuestionResolved,
    RequiresAssistantReassembly,
)
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor


class ListUnansweredQuestionsQuery(ImmutableDTO):
    """
    Questions the assistant could not answer, most frequent first, one page
    at a time.
    """

    business_id: BusinessId
    include_resolved: IsResolvedIncluded = False
    include_sandbox: IsSandboxIncluded = False
    page: PageRequest = Field(default_factory=PageRequest)


class UnansweredQuestionDetails(ImmutableDTO):
    """Unanswered question with how often and when it was last asked."""

    id: UnansweredQuestionId
    business_id: BusinessId
    question: UnansweredQuestionText
    language: LanguageTag
    occurrence_count: QuestionOccurrenceCount
    last_seen_at: Microseconds
    is_resolved: IsUnansweredQuestionResolved
    resolved_knowledge_item_id: KnowledgeItemId | None = None
    is_sandbox: IsSandboxConversation = False


class UnansweredQuestionPage(ImmutableDTO):
    """
    One page of questions, the most asked first, then the most recently
    asked; `next_cursor` asks for the next page (None on the last one).
    """

    items: list[UnansweredQuestionDetails] = Field(
        default_factory=list[UnansweredQuestionDetails]
    )
    next_cursor: PageCursor | None = None


class AnswerUnansweredQuestionRequest(ImmutableDTO):
    """Body of "add answer": the answer and an optional FAQ title."""

    answer: KnowledgeBody
    title: KnowledgeTitle | None = None


class AnswerUnansweredQuestionCommand(ImmutableDTO):
    """
    Owner answers a question; the answer becomes an active FAQ item.

    The FAQ title defaults to the question text.
    """

    business_id: BusinessId
    question_id: UnansweredQuestionId
    answer: KnowledgeBody
    title: KnowledgeTitle | None = None


class AnsweredQuestionResult(ImmutableDTO):
    """
    The resolved question and the new FAQ item. The assistant must be
    reassembled (and autotested) before customers see the answer.
    """

    question: UnansweredQuestionDetails
    knowledge_item_id: KnowledgeItemId
    requires_reassembly: RequiresAssistantReassembly
