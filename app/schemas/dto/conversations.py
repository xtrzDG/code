from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import (
    IsConversationHandedOff,
    IsLlmToolError,
    IsSandboxConversation,
    ShouldEndCall,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    CustomerName,
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)


class InboundMessage(ImmutableDTO):
    """
    A customer message from any channel, normalized.

    `assistant_version_id` pins a specific version (owner test chat,
    autotests); otherwise the business's active version answers.
    """

    business_id: BusinessId
    channel: ChannelKind
    channel_user_id: ChannelUserId
    text: MessageText
    customer_name: CustomerName | None = None
    customer_phone_number: E164PhoneNumber | None = None
    is_sandbox: IsSandboxConversation = False
    assistant_version_id: AssistantVersionId | None = None


class AssistantReply(ImmutableDTO):
    """What the assistant answered and what happened during the turn."""

    conversation_id: ConversationId
    text: MessageText
    language: LanguageTag
    is_handed_off: IsConversationHandedOff
    should_end_call: ShouldEndCall = False
    created_booking_ids: list[BookingId] = Field(default_factory=list[BookingId])
    created_lead_ids: list[LeadId] = Field(default_factory=list[LeadId])
    created_handoff_ids: list[HandoffId] = Field(default_factory=list[HandoffId])


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


class LlmRequest(ImmutableDTO):
    """
    One language-model request.

    `transcript` is the verbatim, append-only list of provider payloads built
    by the same adapter (user text turns, assistant turns, tool result turns).
    """

    model_id: LlmModelId
    system_prompt: SystemPromptText
    tools: list[LlmToolDefinition]
    transcript: list[LlmProviderPayload]
    max_output_tokens: LlmMaxOutputTokens
    effort: LlmEffort


class LlmResponse(ImmutableDTO):
    """Normalized language-model answer plus its verbatim payload to append."""

    stop_reason: LlmStopReason
    text: MessageText | None = None
    tool_calls: list[LlmToolCall] = Field(default_factory=list[LlmToolCall])
    assistant_turn_payload: LlmProviderPayload


class CallGreetingRequest(ImmutableDTO):
    """Ask for the opening line of a phone call answered by the assistant."""

    business_id: BusinessId
    language: LanguageTag | None = None


class CallGreeting(ImmutableDTO):
    """
    Opening line of a call: AI disclosure, recording notice, how to reach a human.
    """

    text: MessageText
    language: LanguageTag
