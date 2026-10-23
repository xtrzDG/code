"""
Twilio's voice webhooks of the call fallback: the addresses, Twilio's
signature and the TwiML answers.

When the voice platform cannot take a call to a rented number (its
address refused the call or did not answer in time), Twilio requests the
number's VoiceFallbackUrl, the business's own address. Twilio signs each request in the
`X-Twilio-Signature` header: base64 of HMAC-SHA1, keyed with the
account's auth token, over the full address it requested followed by
every form field's name and value, sorted by name.
"""

import base64
import hashlib
import hmac
from collections.abc import Mapping, Sequence
from html import escape
from urllib.parse import parse_qsl

from app.schemas.constants.calls import MissedCallReason
from app.schemas.typings.businesses.prefixed_id import BusinessId

# One address per business: the business is known before anything is read,
# and the signature covers it.
TWILIO_VOICE_FALLBACK_PATH_TEMPLATE: str = (
    "/v1/telephony/twilio/voice-fallback/{business_id}"
)
TWILIO_FALLBACK_DIAL_PATH_TEMPLATE: str = (
    "/v1/telephony/twilio/voice-fallback/{business_id}/dial-status"
)
TWILIO_SIGNATURE_HEADER: str = "X-Twilio-Signature"
# How long the staff mobile rings: shorter than a mobile's usual
# forward-on-no-answer (25-30 s), so an unanswered mobile does not send
# the caller back to the assistant's number.
DIAL_TIMEOUT_SECONDS: int = 20
MAX_FORM_FIELDS: int = 64
# How a call to the staff mobile that nobody took ended ("completed" and
# "answered": someone took it).
UNANSWERED_DIAL_STATUSES: Mapping[str, MissedCallReason] = {
    "busy": MissedCallReason.BUSY,
    "no-answer": MissedCallReason.NO_ANSWER,
    "failed": MissedCallReason.LINE_FAILED,
    "canceled": MissedCallReason.ABANDONED,
}


def build_voice_fallback_path(business_id: BusinessId) -> str:
    """The call fallback address of a business's rented numbers."""

    return TWILIO_VOICE_FALLBACK_PATH_TEMPLATE.format(business_id=business_id)


def build_fallback_dial_path(business_id: BusinessId) -> str:
    """Where Twilio reports how the call put through to staff ended."""

    return TWILIO_FALLBACK_DIAL_PATH_TEMPLATE.format(business_id=business_id)


def read_form_pairs(body: bytes) -> list[tuple[str, str]]:
    """Every field of a form-encoded body, in order (repeated names kept)."""

    try:
        text: str = body.decode("utf-8")
    except UnicodeDecodeError:
        return []

    try:
        return parse_qsl(text, keep_blank_values=True, max_num_fields=MAX_FORM_FIELDS)
    except ValueError:
        return []


def first_values(pairs: Sequence[tuple[str, str]]) -> dict[str, str]:
    """The first value of every field."""

    fields: dict[str, str] = {}
    for name, value in pairs:
        fields.setdefault(name, value)
    return fields


def is_valid_twilio_signature(
    auth_token: str,
    url: str,
    pairs: Sequence[tuple[str, str]],
    signature: str | None,
) -> bool:
    """Twilio's signature of a POST to `url` with these form fields."""

    if signature is None or not signature.strip():
        return False

    signed: str = url + "".join(name + value for name, value in sorted(pairs))
    digest: bytes = hmac.new(
        auth_token.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1
    ).digest()
    return hmac.compare_digest(
        base64.b64encode(digest), signature.strip().encode("utf-8")
    )


def build_dial_twiml(number: str, action_url: str) -> str:
    """
    Put the caller through to `number`: it rings DIAL_TIMEOUT_SECONDS, the
    caller hears ringing until someone answers (answerOnBridge) and sees
    their own number, and Twilio reports how it ended to `action_url`.
    """

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Dial timeout="{DIAL_TIMEOUT_SECONDS}" answerOnBridge="true" '
        f'action="{escape(action_url, quote=True)}" method="POST">'
        f"<Number>{escape(number, quote=True)}</Number>"
        "</Dial>"
        "</Response>"
    )


def build_hangup_twiml() -> str:
    """End the call."""

    return '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'


def read_unanswered_reason(dial_status: str) -> MissedCallReason | None:
    """
    Why the staff mobile did not take the call; None when someone did or
    the status is unknown.
    """

    return UNANSWERED_DIAL_STATUSES.get(dial_status.strip().lower())
