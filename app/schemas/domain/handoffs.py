from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffStatus,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.booleans import IsUnansweredQuestionResolved
from app.schemas.typings.handoffs.constrained_integers import (
    QuestionOccurrenceCount,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffQuotedText,
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import LanguageTag


class HandoffDocument(BaseDocument):
    """
    Conversation passed to staff (concept table `handoffs`).

    `summary` is what staff read: the model's own summary (written in the
    staff language), or, for a handoff the platform created, the
    `summary_code` rendered in the business's staff language. The code,
    `quoted_text` and `flagged_values` let the cabinet and notifications
    render it again in each reader's language.

    Version 2: `summary_code`, `quoted_text` and `flagged_values` (all
    optional, so version 1 rows read as they are).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: HandoffId = Field(default_factory=HandoffId)
    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    reason: HandoffReason
    summary: HandoffSummary
    summary_code: HandoffSummaryCode | None = None
    quoted_text: HandoffQuotedText | None = None
    flagged_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
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
