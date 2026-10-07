"""
Callers who did not get through: how a source reports one, the request of
the telephony line's webhook, and what registering one did.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackStatus,
)
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport, RecordedCall
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.booleans import IsNewMissedCall
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput


class MissedCallReport(ImmutableDTO):
    """
    A call whose caller did not get through, as its source reported it.

    The business is known for a call the voice platform stored
    (`business_id`); otherwise it is the one whose phone line was called
    (`assistant_number`). Numbers are read later with the business's
    country as a hint.
    """

    source: MissedCallSource
    provider_call_id: ProviderCallId
    reason: MissedCallReason
    called_at: Microseconds
    business_id: BusinessId | None = None
    assistant_number: RawPhoneNumberInput | None = None
    caller_number: RawPhoneNumberInput | None = None
    language: LanguageTag | None = None
    call_id: CallId | None = None


class StoredFinishedCall(ImmutableDTO):
    """A call the voice platform finished, as it reported it and as it was stored."""

    report: FinishedCallReport
    call: RecordedCall


class RegisteredMissedCall(ImmutableDTO):
    """A missed call as stored, and whether this report stored it first."""

    missed_call: MissedCallDocument
    is_new: IsNewMissedCall


class PbxCallWebhookRequest(ImmutableDTO):
    """A notification of the telephony line, before its signature is checked."""

    body: bytes
    signature_header: WebhookSignatureHeader | None = None


class PbxCallWebhookOutcome(ImmutableDTO):
    """
    What one telephony notification did: IGNORED (not a missed call, or a
    line no business has), RECORDED (a new missed call) or DUPLICATE.
    """

    status: PostCallEventStatus
    missed_call_id: MissedCallId | None = None
    text_back_status: TextBackStatus | None = None


class TextBackJobPayload(ImmutableDTO):
    """The job that sends the text-back of one missed call."""

    missed_call_id: MissedCallId
