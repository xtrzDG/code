from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import CustomerName
from app.schemas.typings.handoffs.booleans import IsUnansweredQuestionResolved
from app.schemas.typings.handoffs.constrained_integers import (
    QuestionOccurrenceCount,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.questionnaires.strings import FaqAnswerText


class HandoffDocument(BaseDocument):
    """Conversation passed to staff with a short summary and the contact."""

    id: HandoffId = Field(default_factory=HandoffId)
    business_id: BusinessId
    conversation_id: ConversationId
    reason: HandoffReason
    summary: HandoffSummary
    customer_name: CustomerName | None = None
    customer_phone_number: E164PhoneNumber | None = None
    channel: ChannelKind
    language: LanguageTag
    status: HandoffStatus = HandoffStatus.PENDING
    is_sandbox: IsSandboxConversation = False


class UnansweredQuestionDocument(BaseDocument):
    """Customer question missing from the business facts ("what to add")."""

    id: UnansweredQuestionId = Field(default_factory=UnansweredQuestionId)
    business_id: BusinessId
    conversation_id: ConversationId | None = None
    question: UnansweredQuestionText
    language: LanguageTag
    occurrence_count: QuestionOccurrenceCount = QuestionOccurrenceCount(1)
    is_resolved: IsUnansweredQuestionResolved = False
    answer: FaqAnswerText | None = None
    is_sandbox: IsSandboxConversation = False
