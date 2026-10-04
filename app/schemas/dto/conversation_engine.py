"""Steps of one customer-message turn inside the conversation engine."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.conversation_engine import ReplyFailureKind, TurnGate
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, ToolCallRecord
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.assistant_tools import AssistantToolContext, AssistantToolOutcome
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.conversations.booleans import (
    IsConversationHandedOff,
    IsFirstAssistantReply,
    IsNewConversation,
    ShouldEndCall,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)


class PreparedTurn(ImmutableDTO):
    """
    A customer message after the engine found its business, contact,
    conversation and pinned assistant version and stored it.

    `context_line` is the server-written preamble (local date and time,
    channel, known phone, notes) placed before the customer's text in the
    model's user turn; `tool_context` is what tools run with.
    `customer_text` is everything the customer said, readable (typed text,
    captions and voice-note transcripts); `model_text` is the message as the
    model reads it (the same, with lines that say what was a voice note, a
    photo or a place); `attachments` are those of the message.
    `reply_message_id` is the id the reply must be stored under (chosen by
    the inbox), None for a new one.
    `reply_language` is the language the customer writes in, any BCP 47
    tag, also one the business did not list: the AI disclosure, the
    platform's notices and the reply use it. `script_hint` is set when the
    customer types that language in another script ("Latn" for Georgian
    written in Latin letters).
    """

    business: BusinessDocument
    version: AssistantVersionDocument
    contact: ContactDocument
    conversation: ConversationDocument
    reply_language: LanguageTag
    script_hint: ScriptCode | None = None
    gate: TurnGate
    is_new_conversation: IsNewConversation
    is_first_reply: IsFirstAssistantReply
    customer_text: MessageText
    model_text: MessageText
    attachments: list[MessageAttachment] = Field(
        default_factory=list[MessageAttachment]
    )
    reply_message_id: MessageId | None = None
    context_line: MessageText
    tool_context: AssistantToolContext
    received_at: Microseconds


class GeneratedReply(ImmutableDTO):
    """
    Outcome of the language-model loop for one turn.

    `text` is None when `failure` is set: the engine then passes the
    conversation to staff and answers with a localized text instead.
    """

    text: MessageText | None = None
    failure: ReplyFailureKind | None = None
    guard_verdict: ReplyGuardVerdict = ReplyGuardVerdict.CLEAN
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    tool_calls: list[ToolCallRecord] = Field(default_factory=list[ToolCallRecord])
    created_booking_ids: list[BookingId] = Field(default_factory=list[BookingId])
    created_lead_ids: list[LeadId] = Field(default_factory=list[LeadId])
    created_handoff_ids: list[HandoffId] = Field(default_factory=list[HandoffId])
    model_id: LlmModelId
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)


class ReplyRecord(ImmutableDTO):
    """
    Everything needed to store the assistant's answer of one turn.

    `text` None means silence (staff own the conversation, or the contact is
    past the message limit).
    """

    turn: PreparedTurn
    text: MessageText | None = None
    guard_verdict: ReplyGuardVerdict = ReplyGuardVerdict.CLEAN
    tool_calls: list[ToolCallRecord] = Field(default_factory=list[ToolCallRecord])
    created_booking_ids: list[BookingId] = Field(default_factory=list[BookingId])
    created_lead_ids: list[LeadId] = Field(default_factory=list[LeadId])
    created_handoff_ids: list[HandoffId] = Field(default_factory=list[HandoffId])
    model_id: LlmModelId | None = None
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)
    is_handed_off: IsConversationHandedOff = False
    should_end_call: ShouldEndCall = False


class VoiceToolCallRecord(ImmutableDTO):
    """A finished voice-agent tool call to keep in the conversation feed."""

    context: AssistantToolContext
    call: LlmToolCall
    outcome: AssistantToolOutcome
