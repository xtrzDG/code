from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.booleans import IsOpenNow
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.booleans import (
    HasCallRecording,
    IsCallConfirmationSent,
)
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.channels.strings import (
    PresentedWebhookSecret,
    WebhookSignatureHeader,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    MessageText,
    ProviderCallId,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput

# --- Requests from the voice agent during a call ---------------------------


class VoiceWebhookCredentials(ImmutableDTO):
    """
    How a voice-agent webhook proves it belongs to a business.

    The agent of each business sends the business id and the business's tool
    secret in headers; a caller that can sign may instead send an HMAC-SHA256
    signature of the raw body made with that secret.
    """

    business_id: BusinessId
    tool_secret: PresentedWebhookSecret | None = Field(default=None, repr=False)
    body_signature: WebhookSignatureHeader | None = None


class VoiceToolWebhookRequest(ImmutableDTO):
    """One tool call of the voice agent, exactly as it arrived."""

    tool_name: AssistantToolName
    credentials: VoiceWebhookCredentials
    body: bytes


class VoiceToolCallArguments(ImmutableDTO):
    """
    The parts of a voice tool webhook body: the model's arguments as JSON,
    the call id and the caller id filled in by the voice platform, and the
    language the model reports the caller speaks.
    """

    input_json: LlmToolInputJson
    provider_call_id: ProviderCallId
    caller_number: RawPhoneNumberInput | None = None
    language: LanguageTag | None = None


class CallInitiationWebhookRequest(ImmutableDTO):
    """The voice platform asks how to start a call (first phrase, language)."""

    credentials: VoiceWebhookCredentials
    body: bytes


class CallInitiationData(ImmutableDTO):
    """
    How the agent starts the call: the greeting with the AI disclosure and
    recording notice, in the business's default language, and whether the
    business is open now (a call is put through to staff only then).
    """

    business_id: BusinessId
    first_message: MessageText
    language: LanguageTag
    caller_phone_number: E164PhoneNumber | None = None
    is_open_now: IsOpenNow = False


# --- Post-call webhook -----------------------------------------------------


class PostCallWebhookRequest(ImmutableDTO):
    """Post-call webhook of the voice platform, before its signature is checked."""

    body: bytes
    signature_header: WebhookSignatureHeader | None = None


class FinishedCallTranscriptLine(ImmutableDTO):
    """One line of a call transcript."""

    author: MessageAuthor
    text: MessageText
    offset_seconds: CallOffsetSeconds


class FinishedCallReport(ImmutableDTO):
    """
    A finished call as the voice platform reports it.

    `assistant_number` is the number that was called (the business's assistant
    line); `caller_number` is read later with the business country as a hint.
    """

    provider_call_id: ProviderCallId
    agent_id: VoiceAgentId | None = None
    assistant_number: RawPhoneNumberInput | None = None
    caller_number: RawPhoneNumberInput | None = None
    started_at: Microseconds
    duration_seconds: CallDurationSeconds
    transcript: list[FinishedCallTranscriptLine] = Field(
        default_factory=list[FinishedCallTranscriptLine]
    )
    called_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
    cost_micro_usd: CostMicroUsd = CostMicroUsd(0)
    language: LanguageTag | None = None
    has_recording: HasCallRecording = False
    # When the agent put the caller through to staff (seconds into the call).
    transfer_offset_seconds: CallOffsetSeconds | None = None


class RecordedCall(ImmutableDTO):
    """
    A finished call stored in `calls`, with what the call produced.

    `is_new` is False when the platform repeated a webhook that was already
    stored; nothing is billed or sent twice then.
    """

    status: PostCallEventStatus
    business_id: BusinessId | None = None
    call_id: CallId | None = None
    conversation_id: ConversationId | None = None
    contact_id: ContactId | None = None
    outcome: CallOutcome | None = None
    booking_ids: list[BookingId] = Field(default_factory=list[BookingId])
    language: LanguageTag | None = None


class PostCallWebhookOutcome(ImmutableDTO):
    """Result of one post-call webhook."""

    status: PostCallEventStatus
    call_id: CallId | None = None
    outcome: CallOutcome | None = None
    is_confirmation_sent: IsCallConfirmationSent = False
