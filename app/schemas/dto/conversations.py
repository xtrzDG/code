from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import LlmStopReason, ReplyGuardVerdict
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.conversation_feed.conversation_views import ToolCallView
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    LlmCallRetryLimit,
    LlmCallTimeoutSeconds,
    LlmMaxOutputTokens,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import (
    IsConversationHandedOff,
    IsLlmToolError,
    IsReplyDeferred,
    IsSandboxConversation,
    ShouldEndCall,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
    ProviderCallId,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag


class InboundMessage(ImmutableDTO):
    """
    A customer message from any channel, normalized (concept: InboundMessage).

    `assistant_version_id` pins a specific version (owner test chat,
    autotests); otherwise the business's published version answers. The
    business comes from the server-side channel lookup, never from the model.
    `customer_message_id` and `reply_message_id` (from the inbox) are the
    ids the customer's message and the reply are stored under, so a turn
    that runs again after a crash stores each of them once. `attachments`
    are the voice notes (transcribed), photos (stored) and places the
    worker read from the message, and what it could not read.

    `waiting_since` is when the platform delivered the customer's first
    unanswered message (the reply's latency counts from it; None: not
    measured). `is_reply_deferred`: the customer wrote again right after,
    so this message is stored and answered together with the next one.
    `acquisition_source` is where the customer came from when the message
    carried it; a conversation the message starts keeps it.
    """

    business_id: BusinessId
    channel: ChannelKind
    channel_user_id: ChannelUserId
    text: MessageText
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    customer_message_id: MessageId | None = None
    reply_message_id: MessageId | None = None
    is_sandbox: IsSandboxConversation = False
    assistant_version_id: AssistantVersionId | None = None
    attachments: list[MessageAttachment] = Field(
        default_factory=list[MessageAttachment]
    )
    waiting_since: Microseconds | None = None
    is_reply_deferred: IsReplyDeferred = False
    acquisition_source: AcquisitionSourceTag | None = None


class AssistantReply(ImmutableDTO):
    """
    What the assistant answered and what happened during the turn.

    `text` is None when the assistant stays silent because staff took over the
    conversation (open handoff in a chat channel). `disclosure_text` is the
    "I am an AI assistant" sentence the server put in front of the first
    reply (part of `text`), so checks of what the model wrote can leave it
    out. `assistant_version_id` and `assistant_version_number` name the
    version that answered (the one the conversation is pinned to);
    `tool_calls` are the tools the model called in this turn, with their
    input and result (the owner's test chat shows them).
    """

    conversation_id: ConversationId
    text: MessageText | None
    disclosure_text: MessageText | None = None
    language: LanguageTag
    is_handed_off: IsConversationHandedOff
    guard_verdict: ReplyGuardVerdict = ReplyGuardVerdict.CLEAN
    should_end_call: ShouldEndCall = False
    created_booking_ids: list[BookingId] = Field(default_factory=list[BookingId])
    created_lead_ids: list[LeadId] = Field(default_factory=list[LeadId])
    created_handoff_ids: list[HandoffId] = Field(default_factory=list[HandoffId])
    assistant_version_id: AssistantVersionId | None = None
    assistant_version_number: AssistantVersionNumber | None = None
    tool_calls: list[ToolCallView] = Field(default_factory=list[ToolCallView])


class LlmToolDefinition(ImmutableDTO):
    """Tool offered to the language model."""

    name: AssistantToolName
    description: LlmToolDescription
    input_schema_json: LlmToolInputSchemaJson


class LlmToolCall(ImmutableDTO):
    """Tool call requested by the language model."""

    call_id: LlmToolCallId
    tool_name: AssistantToolName
    input_json: LlmToolInputJson


class LlmToolResult(ImmutableDTO):
    """Result of executing one tool call."""

    call_id: LlmToolCallId
    result_json: LlmToolResultJson
    is_error: IsLlmToolError = False


class LlmCallLimits(ImmutableDTO):
    """
    How long one model call may take and how often it is retried: a
    customer waits for the answer, so the chat path bounds both.
    """

    timeout_seconds: LlmCallTimeoutSeconds
    retry_limit: LlmCallRetryLimit


class LlmRequest(ImmutableDTO):
    """
    One language-model request.

    `transcript` is the verbatim, append-only list of payloads: user and tool
    result turns in the canonical format of app/adapters/llm/llm_payloads.py,
    assistant turns in the provider's own format. The model id selects the
    provider adapter.
    """

    model_id: LlmModelId
    system_prompt: SystemPromptText
    tools: list[LlmToolDefinition]
    transcript: list[LlmProviderPayload]
    max_output_tokens: LlmMaxOutputTokens
    effort: LlmEffort
    # None: the provider client's own timeout and retries (long background
    # work such as autotest judges and menu imports).
    call_limits: LlmCallLimits | None = None
    # The same transcript in the provider-neutral form (assistant turns as
    # text and tool calls, without a provider's reasoning): what a model of
    # another provider is sent when this request's model fails. None: the
    # transcript is used as it is.
    fallback_transcript: list[LlmProviderPayload] | None = None


class LlmResponse(ImmutableDTO):
    """
    Normalized language-model answer plus its verbatim payload to append.
    `fallback_model_id` names the model that answered instead of the
    requested one (its provider failed or its circuit was open).
    """

    stop_reason: LlmStopReason
    text: MessageText | None = None
    tool_calls: list[LlmToolCall] = Field(default_factory=list[LlmToolCall])
    assistant_turn_payload: LlmProviderPayload
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)
    fallback_model_id: LlmModelId | None = None


class CallGreetingRequest(ImmutableDTO):
    """Ask for the first phrase of a phone call answered by the assistant."""

    business_id: BusinessId
    language: LanguageTag | None = None


class CallGreeting(ImmutableDTO):
    """
    First phrase of a call (concept section 7): who answers (AI assistant of
    the business), that the call is recorded, how to reach a human.
    """

    text: MessageText
    language: LanguageTag


class VoiceToolCallRequest(ImmutableDTO):
    """
    A tool call made by the voice agent during a phone call (concept section 7:
    tools are our webhooks). The business comes from the verified webhook.
    """

    business_id: BusinessId
    provider_call_id: ProviderCallId
    caller_phone_number: E164PhoneNumber | None = None
    tool_name: AssistantToolName
    input_json: LlmToolInputJson
    language: LanguageTag | None = None


class VoiceToolCallResult(ImmutableDTO):
    """Tool result returned to the voice agent (target: under one second)."""

    result_json: LlmToolResultJson
    is_error: IsLlmToolError = False
