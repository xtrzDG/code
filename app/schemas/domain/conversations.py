from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import (
    ChannelKind,
    InboundContextNote,
    MessageDirection,
)
from app.schemas.constants.conversations import (
    CallGuardVerdict,
    CallOutcome,
    ConversationRating,
    ConversationRatingReason,
    ConversationStatus,
    LlmTurnRole,
    MessageAuthor,
    ReplyGuardVerdict,
)
from app.schemas.constants.reply_safety import (
    ClaimTopic,
    ClaimVerdict,
    InjectionSignal,
    ReplyGuardReason,
)
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import (
    AwaitsImprovement,
    IsAfterHours,
    IsFallbackModel,
    IsLlmToolError,
    IsSandboxConversation,
)
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
    LlmRoundCount,
    LlmTokenCount,
    LlmTurnSequenceNumber,
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
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
    ClaimText,
    LlmProviderPayload,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
    ProviderCallId,
    RecordingStoragePath,
    UnverifiedReplyValue,
)
from app.schemas.typings.inbox.booleans import AwaitsTeam, HasOpenRequest
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.schemas.typings.users.prefixed_id import UserId


class ConversationDocument(BaseDocument):
    """
    Customer conversation in one channel (concept table `conversations`).

    Pinned to one assistant version so its instruction and tools never change
    mid-conversation. `rating` is the owner's or staff's good / bad verdict.

    The team inbox fields belong to their own operations, and a plain save
    of the conversation keeps their stored values
    (`ConversationRepoContract.save`): the assignment (`assignee_user_id`,
    who assigned it, when, and `assignment_revision`, the compare-and-set
    version) changes only through `ConversationTeamRepoContract.assign`,
    `has_open_request` (a request of the conversation is new or in
    progress) only through `set_open_request`. `awaits_team` is derived on
    every write: the conversation needs a person (HANDOFF) or has an open
    request. `assigned_by` is None for an automatic assignment.

    Version 2: the team inbox fields (all optional, so version 1 rows read
    as they are).

    Version 3: `acquisition_source`, where the customer came from when the
    conversation started (a shared link's tag, an ad, the number dialled;
    `app/utilities/sharing/acquisition_sources.py`). Set once, never
    changed; optional, so version 2 rows read as they are.

    Version 4: why a bad rating was given (`rating_reason`), the answer it
    is about (`rated_message_id`), when someone acted on it (corrected the
    answer or saved a check from it: `improved_at`) and, derived on every
    review write, whether it still waits for that (`awaits_improvement`,
    the Overview's "Answers worth improving"). The review fields change
    only through `ConversationReviewRepoContract.set_review`; a plain save
    keeps them as stored. All optional, so version 3 rows read as they are.

    Version 5: what the conversation was about (`summary`, at most 300
    characters, written by a cheap model once it was quiet for two hours)
    and when (`summarized_at`), the assistant's memory of a returning
    customer. Optional, so version 4 rows read as they are.
    """

    schema_version: SchemaVersion = SchemaVersion("5")
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
    assignee_user_id: UserId | None = None
    assigned_by: UserId | None = None
    assigned_at: Microseconds | None = None
    assignment_revision: AssignmentRevision = AssignmentRevision(0)
    has_open_request: HasOpenRequest = False
    awaits_team: AwaitsTeam = False
    acquisition_source: AcquisitionSourceTag | None = None
    rating_reason: ConversationRatingReason | None = None
    rated_message_id: MessageId | None = None
    improved_at: Microseconds | None = None
    awaits_improvement: AwaitsImprovement = False
    summary: ConversationSummaryText | None = None
    summarized_at: Microseconds | None = None


class ToolCallRecord(PersistentDocument):
    """One tool call made while producing a message (concept tool_calls_json)."""

    tool_name: AssistantToolName
    input_json: LlmToolInputJson
    result_json: LlmToolResultJson
    is_error: IsLlmToolError = False


class ClaimFinding(PersistentDocument):
    """One policy or availability claim of a reply and what the check found."""

    claim: ClaimText
    topic: ClaimTopic
    verdict: ClaimVerdict


class MessageDocument(BaseDocument):
    """
    Stored message with model usage and cost (concept table `messages`).

    `sent_by` is the owner or staff member who wrote a STAFF message from
    the cabinet. `text` is what the author wrote (for a customer, the typed
    text and captions); `attachments` are the voice notes, photos, places
    and other files of a customer message, with the transcript of a voice
    note.

    Version 2: `attachments` (optional, so version 1 rows read as they are).

    Version 3: how an assistant reply was made, for reply-speed metrics:
    `channel` (the conversation's, so latency groups per channel in the
    database), `reply_latency_ms` (from the platform delivering the
    customer's first unanswered message to the reply being stored; None
    when not measured, e.g. test chats and older rows), `llm_round_count`
    and `is_fallback_model` (a model of the other provider answered because
    the version's own failed). All optional, so version 2 rows read as they
    are.

    Version 4: what the reply guard did (R10). On an assistant reply:
    `guard_verdict` (clean, rewritten once, handed to staff; None on other
    messages and older rows), `guard_reasons` (why it was held back),
    `unverified_values` (values the evidence did not back, as written) and
    `claim_findings` (each policy or availability claim the verifier
    checked). On a customer message: `injection_flag`, the kind of prompt
    injection it looked like (None: none). All optional, so version 3 rows
    read as they are.

    Version 5: `tool_calls` may name the tool list_my_bookings (a new
    value; version 4 rows read as they are). Version 6: they may name the
    tool join_waitlist (a new value; version 5 rows read as they are).

    Version 7 (R14): an assistant reply may offer `choices` (the options
    shown as buttons, quick replies or chips; its text already ends with
    their prompt), and a customer message may say what it refers to
    (`context_note`, e.g. a reply to the business's Instagram story). Both
    optional. `tool_calls` may name offer_choices once its release gate is
    open (a new value).
    """

    schema_version: SchemaVersion = SchemaVersion("7")
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
    attachments: list[MessageAttachment] = Field(
        default_factory=list[MessageAttachment]
    )
    channel: ChannelKind | None = None
    reply_latency_ms: ReplyLatencyMilliseconds | None = None
    llm_round_count: LlmRoundCount = LlmRoundCount(0)
    is_fallback_model: IsFallbackModel = False
    guard_verdict: ReplyGuardVerdict | None = None
    guard_reasons: list[ReplyGuardReason] = Field(
        default_factory=list[ReplyGuardReason]
    )
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    claim_findings: list[ClaimFinding] = Field(default_factory=list[ClaimFinding])
    injection_flag: InjectionSignal | None = None
    choices: ReplyChoices | None = None
    context_note: InboundContextNote | None = None


class LlmTurnDocument(BaseDocument):
    """
    One raw language-model turn, stored verbatim and only ever appended.

    The turns of a conversation are replayed to the model in order.

    Version 2: `canonical_payload`, the turn in the provider-neutral form
    (an assistant turn's text and tool calls, without the provider's
    reasoning or signatures) that a model of another provider is sent when
    the conversation's own model fails. None: `payload` is already
    canonical (user and tool-result turns, turns stored before version 2).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: LlmTurnId = Field(default_factory=LlmTurnId)
    conversation_id: ConversationId
    sequence_number: LlmTurnSequenceNumber
    role: LlmTurnRole
    payload: LlmProviderPayload
    canonical_payload: LlmProviderPayload | None = None


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
