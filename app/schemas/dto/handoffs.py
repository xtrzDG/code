from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import CustomerName
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)


class HandoffCommand(ImmutableDTO):
    """Pass a conversation to staff."""

    business_id: BusinessId
    conversation_id: ConversationId
    reason: HandoffReason
    summary: HandoffSummary
    customer_name: CustomerName | None = None
    customer_phone_number: E164PhoneNumber | None = None
    channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class HandoffView(ImmutableDTO):
    """Handoff and whether staff were notified."""

    id: HandoffId
    business_id: BusinessId
    conversation_id: ConversationId
    reason: HandoffReason
    summary: HandoffSummary
    status: HandoffStatus


class RecordUnansweredQuestionCommand(ImmutableDTO):
    """Remember a customer question that the facts did not answer."""

    business_id: BusinessId
    conversation_id: ConversationId | None = None
    question: UnansweredQuestionText
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class UnansweredQuestionView(ImmutableDTO):
    """Unanswered question as stored (deduplicated per business)."""

    id: UnansweredQuestionId
    business_id: BusinessId
    question: UnansweredQuestionText
    language: LanguageTag
