"""
Webhook signatures (SDLC-07): a delivery signed with the secret verifies,
and any change to it is refused: a body with one byte changed, added or
removed, another secret, a changed signature, a moved timestamp (the voice
platform's), another address or another form value (Twilio's).
"""

import base64
import hashlib
import hmac

from hypothesis import assume, given
from hypothesis import strategies as st

from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.calls.twilio_voice_webhooks import is_valid_twilio_signature
from app.utilities.channels.webhook_signatures import (
    is_valid_elevenlabs_signature,
    is_valid_sha256_signature,
    sign_body,
)

NOW: int = 1_791_000_000
LETTERS: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
secrets = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=8, max_size=64
)
bodies = st.binary(min_size=1, max_size=512)
form_fields = st.lists(
    st.tuples(
        st.text(
            alphabet=LETTERS,
            min_size=1,
            max_size=12,
        ),
        st.text(max_size=24),
    ),
    min_size=1,
    max_size=8,
)


@st.composite
def mutated(draw: st.DrawFn, body: bytes) -> bytes:
    """The body with one byte changed, added or removed (never the same)."""

    kind = draw(st.sampled_from(("change", "add", "remove")))
    index = draw(st.integers(0, len(body) - 1))
    if kind == "change":
        flip = draw(st.integers(1, 255))
        return body[:index] + bytes([body[index] ^ flip]) + body[index + 1 :]
    if kind == "add":
        return body[:index] + bytes([draw(st.integers(0, 255))]) + body[index:]
    return body[:index] + body[index + 1 :]


def meta_header(secret: str, body: bytes) -> WebhookSignatureHeader:
    return WebhookSignatureHeader(f"sha256={sign_body(secret, body)}")


def voice_header(secret: str, body: bytes, timestamp: int) -> WebhookSignatureHeader:
    digest = hmac.new(
        secret.encode("utf-8"), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return WebhookSignatureHeader(f"t={timestamp},v0={digest}")


def twilio_signature(token: str, url: str, pairs: list[tuple[str, str]]) -> str:
    signed = url + "".join(name + value for name, value in sorted(pairs))
    return base64.b64encode(
        hmac.new(token.encode(), signed.encode(), hashlib.sha1).digest()
    ).decode()


@given(secrets, bodies, st.data())
def test_a_meta_signature_holds_only_for_its_body_and_secret(
    secret: str, body: bytes, data: st.DataObject
) -> None:
    header = meta_header(secret, body)
    other_body = data.draw(mutated(body))
    other_secret = data.draw(secrets.filter(lambda drawn: drawn != secret))

    assert is_valid_sha256_signature(secret, body, header)
    assert not is_valid_sha256_signature(secret, other_body, header)
    assert not is_valid_sha256_signature(other_secret, body, header)
    assert not is_valid_sha256_signature(secret, body, None)


@given(secrets, bodies, st.integers(0, 63), st.sampled_from("0123456789abcdef"))
def test_a_changed_meta_signature_is_refused(
    secret: str, body: bytes, position: int, digit: str
) -> None:
    digest = sign_body(secret, body)
    assume(digest[position] != digit)
    changed = digest[:position] + digit + digest[position + 1 :]

    assert not is_valid_sha256_signature(
        secret, body, WebhookSignatureHeader(f"sha256={changed}")
    )


@given(secrets, bodies, st.integers(-300, 1_800), st.data())
def test_a_voice_signature_holds_only_for_its_body_time_and_secret(
    secret: str, body: bytes, age: int, data: st.DataObject
) -> None:
    timestamp = NOW - age
    header = voice_header(secret, body, timestamp)
    moved = data.draw(
        st.integers(timestamp - 600, timestamp + 600).filter(lambda t: t != timestamp)
    )
    forged = voice_header(secret, body, timestamp).replace(
        f"t={timestamp}", f"t={moved}"
    )

    assert is_valid_elevenlabs_signature(PlatformSecret(secret), body, header, NOW)
    assert not is_valid_elevenlabs_signature(
        PlatformSecret(secret), data.draw(mutated(body)), header, NOW
    )
    assert not is_valid_elevenlabs_signature(
        PlatformSecret(secret), body, WebhookSignatureHeader(forged), NOW
    )


@given(secrets, bodies, st.integers(1_801, 10**6))
def test_an_old_voice_signature_is_refused_as_a_replay(
    secret: str, body: bytes, age: int
) -> None:
    header = voice_header(secret, body, NOW - age)

    assert not is_valid_elevenlabs_signature(PlatformSecret(secret), body, header, NOW)


@given(secrets, form_fields, st.data())
def test_a_twilio_signature_holds_only_for_its_address_and_fields(
    token: str, pairs: list[tuple[str, str]], data: st.DataObject
) -> None:
    url = "https://api.workshop.example/v1/telephony/twilio/voice-fallback/b_1"
    signature = twilio_signature(token, url, pairs)
    index = data.draw(st.integers(0, len(pairs) - 1))
    name, value = pairs[index]
    changed_value = data.draw(st.text(max_size=24).filter(lambda text: text != value))
    changed = [*pairs[:index], (name, changed_value), *pairs[index + 1 :]]
    assume(sorted(changed) != sorted(pairs))

    assert is_valid_twilio_signature(token, url, pairs, signature)
    assert not is_valid_twilio_signature(token, url + "x", pairs, signature)
    assert not is_valid_twilio_signature(token, url, changed, signature)
    assert not is_valid_twilio_signature(token + "x", url, pairs, signature)
    assert not is_valid_twilio_signature(token, url, pairs, None)
