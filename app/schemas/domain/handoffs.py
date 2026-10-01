from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.booleans import IsUnansweredQuestionResolved
from app.schemas.typings.handoffs.constrained_integers import (
    QuestionOccurrenceCount,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import LanguageTag


class HandoffDocument(BaseDocument):
    """Conversation passed to staff (concept table `handoffs`)."""

    id: HandoffId = Field(default_factory=HandoffId)
    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    reason: HandoffReason
    summary: HandoffSummary
    urgency: HandoffUrgency = HandoffUrgency.NORMAL
    status: HandoffStatus = HandoffStatus.PENDING
    resolved_at: Microseconds | None = None
    is_sandbox: IsSandboxConversation = False


class UnansweredQuestionDocument(BaseDocument):
    """Question missing from the knowledge base (concept `unanswered_questions`)."""

    id: UnansweredQuestionId = Field(default_factory=UnansweredQuestionId)
    business_id: BusinessId
    question: UnansweredQuestionText
    language: LanguageTag
    occurrence_count: QuestionOccurrenceCount = QuestionOccurrenceCount(1)
    last_seen_at: Microseconds
    is_resolved: IsUnansweredQuestionResolved = False
    resolved_knowledge_item_id: KnowledgeItemId | None = None
    is_sandbox: IsSandboxConversation = False
