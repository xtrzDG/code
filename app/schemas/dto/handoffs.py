from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
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
from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.schemas.typings.handoffs.strings import (
    HandoffQuotedText,
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class CodedHandoffSummary(ImmutableDTO):
    """
    The summary of a handoff the platform created: what happened (a code
    each reader's language renders), the words it quotes (the customer's
    message, or the reply that did not arrive) and the values the guard
    flagged.
    """

    code: HandoffSummaryCode
    quoted_text: HandoffQuotedText | None = None
    flagged_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )


class HandoffSummaryInput(ImmutableDTO):
    """A coded handoff summary to render in one reader's language."""

    summary: CodedHandoffSummary
    language: LanguageTag


class HandoffCommand(ImmutableDTO):
    """
    Pass a conversation to staff (concept handoff_to_human).

    The model writes `summary` itself (in the staff language its
    instruction names); the platform passes a `CodedHandoffSummary`, which
    every reader gets in their own language. `language` is the customer's.
    """

    business_id: BusinessId
    conversation_id: ConversationId
    contact_id: ContactId
    reason: HandoffReason
    summary: HandoffSummary | CodedHandoffSummary
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
