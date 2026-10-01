from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class HandoffCommand(ImmutableDTO):
    """Pass a conversation to staff (concept handoff_to_human)."""

    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    reason: HandoffReason
    summary: HandoffSummary
    urgency: HandoffUrgency
    source_channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class HandoffResult(ImmutableDTO):
    """
    Handoff plus what to tell the customer (concept handoff_to_human output):
    "a colleague will reply soon" during working hours, "in the morning"
    outside them, in the customer's language.
    """

    id: HandoffId
    business_id: BusinessId
    conversation_id: ConversationId
    reason: HandoffReason
    urgency: HandoffUrgency
    status: HandoffStatus
    customer_message: MessageText


class RecordUnansweredQuestionCommand(ImmutableDTO):
    """Remember a customer question that the knowledge base did not answer."""

    business_id: BusinessId
    question: UnansweredQuestionText
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False


class UnansweredQuestionView(ImmutableDTO):
    """Unanswered question as stored (deduplicated per business)."""

    id: UnansweredQuestionId
    business_id: BusinessId
    question: UnansweredQuestionText
    language: LanguageTag
