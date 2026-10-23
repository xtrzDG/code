"""
The call fallback: a call the voice platform could not take is put
through to the staff mobile on duty, and the owner hears about it.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.telephony.strings import TwimlDocument


class CallFallbackWebhookRequest(ImmutableDTO):
    """
    A request of the carrier's call fallback to a business's address,
    before its signature (which covers the address) is checked.
    """

    business_id: BusinessId
    body: bytes
    signature_header: WebhookSignatureHeader | None = None


class CallFallbackReport(ImmutableDTO):
    """
    A call the voice platform could not take, as the carrier reported it:
    the number called (the business's line), the caller and, for a call
    forwarded to the line, the number it was forwarded from.
    """

    provider_call_id: ProviderCallId
    called_at: Microseconds
    assistant_number: RawPhoneNumberInput | None = None
    caller_number: RawPhoneNumberInput | None = None
    forwarded_from: RawPhoneNumberInput | None = None


class CallFallbackReply(ImmutableDTO):
    """What the carrier does with the call next (put it through, hang up)."""

    twiml: TwimlDocument


class CallFallbackPlan(ImmutableDTO):
    """
    What a call the voice platform could not take gets: put through to
    `transfer_phone_number`, or a missed call (`missed_call`) when nobody
    can take it. `looping_phone_number` is the staff phone on duty that was
    not rung because the call came from it, was forwarded from it or is
    that very line (ringing it would loop).
    """

    reply: CallFallbackReply
    called_at: Microseconds
    business_id: BusinessId
    transfer_phone_number: E164PhoneNumber | None = None
    looping_phone_number: E164PhoneNumber | None = None
    missed_call: MissedCallReport | None = None


class FallbackDialOutcome(ImmutableDTO):
    """How the call to the staff mobile ended: a missed call when nobody took it."""

    reply: CallFallbackReply
    missed_call: MissedCallReport | None = None
