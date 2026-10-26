"""Twilio's signature, form fields and TwiML of the call fallback."""

import base64
import hashlib
import hmac

import pytest

from app.adapters.telephony.twilio_call_fallback_adapter import (
    TwilioCallFallbackAdapter,
)
from app.schemas.constants.calls import MissedCallReason
from app.schemas.exceptions.application_errors import PreconditionFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.calls.twilio_voice_webhooks import (
    build_dial_twiml,
    first_values,
    is_valid_twilio_signature,
    read_form_pairs,
    read_unanswered_reason,
)
from tests.calls.call_fallback_steps import fallback_settings

URL: str = (
    "https://api.workshop.test/v1/telephony/twilio/voice-fallback/"
    "business_fd43b272-3035-4a74-a29f-96b1631dd8b5"
)
TOKEN: str = "test-token-0000"


def signature_of(url: str, pairs: list[tuple[str, str]]) -> str:
    """Twilio's recipe written out again: the URL, then name+value by name."""

    message = url
    for name, value in sorted(pairs):
        message += name + value
    return base64.b64encode(
        hmac.new(TOKEN.encode(), message.encode(), hashlib.sha1).digest()
    ).decode()


def test_the_signature_covers_the_address_and_every_field() -> None:
    pairs = [("To", "+995322000000"), ("CallSid", "CA1"), ("From", "+995599")]
    signature = signature_of(URL, pairs)

    assert is_valid_twilio_signature(TOKEN, URL, pairs, signature)
    assert is_valid_twilio_signature(TOKEN, URL, pairs, f" {signature}\n")
    assert not is_valid_twilio_signature("another-token", URL, pairs, signature)
    assert not is_valid_twilio_signature(TOKEN, URL + "?x=1", pairs, signature)
    assert not is_valid_twilio_signature(
        TOKEN, URL, [*pairs, ("Digits", "1")], signature
    )
    assert not is_valid_twilio_signature(TOKEN, URL, pairs, None)
    assert not is_valid_twilio_signature(TOKEN, URL, pairs, "  ")


def test_repeated_fields_are_signed_in_order_of_value() -> None:
    pairs = [("Digits", "2"), ("Digits", "1")]

    assert is_valid_twilio_signature(TOKEN, URL, pairs, signature_of(URL, pairs))
    assert first_values(pairs) == {"Digits": "2"}


def test_form_fields_keep_repeats_and_unreadable_bodies_have_none() -> None:
    assert read_form_pairs(b"From=%2B995599&To=&From=2") == [
        ("From", "+995599"),
        ("To", ""),
        ("From", "2"),
    ]
    assert read_form_pairs(b"\xff\xfe") == []
    assert read_form_pairs(b"&".join([b"a=1"] * 65)) == []


def test_the_dial_escapes_what_it_is_given() -> None:
    twiml = build_dial_twiml("+1<2>", 'https://api.example.com/x?a=1&b="2"')

    assert "<Number>+1&lt;2&gt;</Number>" in twiml
    assert 'action="https://api.example.com/x?a=1&amp;b=&quot;2&quot;"' in twiml


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (" No-Answer ", MissedCallReason.NO_ANSWER),
        ("busy", MissedCallReason.BUSY),
        ("completed", None),
        ("answered", None),
        ("", None),
    ],
)
def test_how_the_call_to_the_mobile_ended(
    status: str, reason: MissedCallReason | None
) -> None:
    assert read_unanswered_reason(status) is reason


def test_without_the_address_no_call_is_put_through() -> None:
    adapter = TwilioCallFallbackAdapter(fallback_settings(APP_BASE_URL=""))

    with pytest.raises(PreconditionFailedError, match="APP_BASE_URL"):
        adapter.transfer(
            BusinessId("business_fd43b272-3035-4a74-a29f-96b1631dd8b5"),
            E164PhoneNumber("+995555123456"),
        )
