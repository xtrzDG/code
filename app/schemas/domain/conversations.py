from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    CallGuardVerdict,
    CallOutcome,
    ConversationRating,
    ConversationStatus,
    LlmTurnRole,
    MessageAuthor,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import (
    IsAfterHours,
    IsLlmToolError,
    IsSandboxConversation,
)
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
    LlmTokenCount,
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.prefixed_id import (
    CallId,
    ConversationId,
    LlmTurnId,
    MessageId,
)
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    ChannelUserId,
    LlmProviderPayload,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
    ProviderCallId,
    RecordingStoragePath,
    UnverifiedReplyValue,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId


class ConversationDocument(BaseDocument):
    """
    Customer conversation in one channel (concept table `conversations`).

    Pinned to one assistant version so its instruction and tools never change
    mid-conversation. `rating` is the owner's or staff's good / bad verdict.
    """

    id: ConversationId = Field(default_factory=ConversationId)
    business_id: BusinessId
    contact_id: ContactId
    assistant_version_id: AssistantVersionId
    channel: ChannelKind
    channel_user_id: ChannelUserId
    language: LanguageTag | None = None
    status: ConversationStatus = ConversationStatus.OPEN
    is_after_hours: IsAfterHours = False
    is_sandbox: IsSandboxConversation = False
    last_message_at: Microseconds
    rating: ConversationRating | None = None
    rated_by: UserId | None = None
    rated_at: Microseconds | None = None


class ToolCallRecord(PersistentDocument):
    """One tool call made while producing a message (concept tool_calls_json)."""

    tool_name: AssistantToolName
    input_json: LlmToolInputJson
    result_json: LlmToolResultJson
    is_error: IsLlmToolError = False


class MessageDocument(BaseDocument):
    """
    Stored message with model usage and cost (concept table `messages`).

    `sent_by` is the owner or staff member who wrote a STAFF message from
    the cabinet.
    """

    id: MessageId = Field(default_factory=MessageId)
    conversation_id: ConversationId
    business_id: BusinessId
    direction: MessageDirection
    author: MessageAuthor
    text: MessageText
    language: LanguageTag | None = None
    sent_by: UserId | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list[ToolCallRecord])
    model_id: LlmModelId | None = None
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)


class LlmTurnDocument(BaseDocument):
    """
    One raw language-model turn, stored verbatim and only ever appended.

    The turns of a conversation are replayed to the model in order.
    """

    id: LlmTurnId = Field(default_factory=LlmTurnId)
    conversation_id: ConversationId
    sequence_number: LlmTurnSequenceNumber
    role: LlmTurnRole
    payload: LlmProviderPayload


class CallSummary(PersistentDocument):
    """The summary of a call for staff in one language."""

    language: LanguageTag
    text: CallSummaryText


class CallDocument(BaseDocument):
    """Phone call handled by the voice agent (concept table `calls`)."""

    # 2: `guard_verdict` and `unverified_values` (both optional, so version 1
    # needs no upcaster). 3: `summaries` and `summarized_at` (optional too).
    schema_version: SchemaVersion = SchemaVersion("3")
    id: CallId = Field(default_factory=CallId)
    business_id: BusinessId
    conversation_id: ConversationId | None = None
    from_phone_number: E164PhoneNumber | None = None
    to_phone_number: E164PhoneNumber | None = None
    started_at: Microseconds
    duration_seconds: CallDurationSeconds = CallDurationSeconds(0)
    recording_path: RecordingStoragePath | None = None
    transcript: CallTranscriptText | None = None
    provider_call_id: ProviderCallId
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)
    outcome: CallOutcome | None = None
    # The invented-numbers audit of the assistant's spoken lines; None until
    # the call is audited (calls stored before the audit existed).
    guard_verdict: CallGuardVerdict | None = None
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    # What the caller wanted and how it ended, for staff, in the languages
    # of the business's owner and staff; empty until the call is summarized.
    summaries: list[CallSummary] = Field(default_factory=list[CallSummary])
    summarized_at: Microseconds | None = None
