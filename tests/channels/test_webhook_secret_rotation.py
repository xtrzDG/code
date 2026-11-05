"""
Zero-downtime rotation of webhook secrets: while `<NAME>_PREVIOUS` holds
the old value, a delivery signed with it is accepted as well as one signed
with the current value (tried first); another value is refused, and a
previous value never opens anything on its own.
"""

import base64
import hashlib
import hmac
import time
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.telephony.twilio_call_fallback_adapter import (
    TwilioCallFallbackAdapter,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.adapters.voice.zadarma_pbx_webhook_adapter import ZadarmaPbxWebhookAdapter
from app.clients.flitt.flitt_client import FlittClient
from app.clients.flitt.flitt_protocol import build_parameter_signature
from app.schemas.dto.calls.call_fallback import CallFallbackWebhookRequest
from app.schemas.dto.calls.missed_calls import PbxCallWebhookRequest
from app.schemas.dto.voice_webhooks import PostCallWebhookRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    AuthenticationRequiredError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.calls.twilio_voice_webhooks import build_voice_fallback_path
from tests.channels.channels_payloads import sign_meta
from tests.channels.channels_settings import APP_BASE_URL, build_settings
from tests.channels.meta_payloads import post_meta, whatsapp_message, whatsapp_webhook
from tests.channels.testbed import ChannelsTestbed

OLD: str = "the-secret-before-the-rotation-0000"  # gitleaks:allow
OTHER: str = "a-secret-nobody-configured-00000"  # gitleaks:allow


def test_meta_accepts_the_previous_app_secret_during_a_rotation() -> None:
    testbed = ChannelsTestbed(build_settings(META_APP_SECRET_PREVIOUS=OLD))
    payload = whatsapp_webhook([whatsapp_message("1")])

    current = post_meta(testbed, payload)
    previous = post_meta(testbed, payload, signature=sign_meta(b"x", OLD))
    body = post_meta(testbed, {"object": "user"}, signature=None)

    assert current.status_code == 200
    # A signature over another body is no signature of this one.
    assert previous.status_code == 401
    assert body.status_code == 401


@pytest.mark.parametrize(
    ("settings", "secret", "status"),
    [
        ({"META_APP_SECRET_PREVIOUS": OLD}, OLD, 200),
        ({"META_APP_SECRET_PREVIOUS": OLD}, OTHER, 401),
        ({}, OLD, 401),
        # Without the current value nothing is verified, not even the old one.
        ({"META_APP_SECRET": "", "META_APP_SECRET_PREVIOUS": OLD}, OLD, 401),
    ],
)
def test_meta_signatures_of_the_old_secret(
    settings: dict[str, str], secret: str, status: int
) -> None:
    testbed = ChannelsTestbed(build_settings(**settings))
    client = testbed.build_http_client()
    body = b'{"object": "whatsapp_business_account", "entry": []}'

    response = client.post(
        "/v1/channels/meta/webhook",
        content=body,
        headers={"X-Hub-Signature-256": sign_meta(body, secret)},
    )

    assert response.status_code == status


def elevenlabs_header(
    secret: str, body: bytes, timestamp: int
) -> WebhookSignatureHeader:
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return WebhookSignatureHeader(f"t={timestamp},v0={digest}")


@pytest.mark.parametrize(("secret", "is_accepted"), [(OLD, True), (OTHER, False)])
def test_elevenlabs_post_call_signed_with_the_previous_secret(
    secret: str, is_accepted: bool
) -> None:
    adapter = ElevenLabsVoiceWebhookAdapter(
        build_settings(ELEVENLABS_WEBHOOK_SECRET_PREVIOUS=OLD)
    )
    now = int(time.time())
    body = b'{"type": "post_call_transcription"}'
    request = PostCallWebhookRequest(
        body=body, signature_header=elevenlabs_header(secret, body, now)
    )

    if is_accepted:
        adapter.verify_post_call_signature(request, Microseconds(now * 1_000_000))
    else:
        with pytest.raises(AuthenticationRequiredError):
            adapter.verify_post_call_signature(request, Microseconds(now * 1_000_000))


def zadarma_request(secret: str) -> PbxCallWebhookRequest:
    fields = {
        "event": "NOTIFY_END",
        "caller_id": "+995555123456",
        "called_did": "+995322000000",
        "call_start": "2026-10-05 12:00:00",
    }
    signed = (
        fields["caller_id"] + fields["called_did"] + fields["call_start"]
    ).encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha1).hexdigest()
    return PbxCallWebhookRequest(
        body=urlencode(fields).encode(),
        signature_header=WebhookSignatureHeader(
            base64.b64encode(digest.encode()).decode()
        ),
    )


@pytest.mark.parametrize(("secret", "is_accepted"), [(OLD, True), (OTHER, False)])
def test_zadarma_notifications_signed_with_the_previous_secret(
    secret: str, is_accepted: bool
) -> None:
    moment = int(datetime(2026, 10, 5, 12, 0, 30, tzinfo=UTC).timestamp())
    adapter = ZadarmaPbxWebhookAdapter(
        build_settings(ZADARMA_API_SECRET_PREVIOUS=OLD),
        InMemoryRateLimitBucketAdapter(),
        WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: moment * 1_000_000_000,
        ),
    )

    if is_accepted:
        adapter.verify_signature(zadarma_request(secret))
    else:
        with pytest.raises(AuthenticationRequiredError):
            adapter.verify_signature(zadarma_request(secret))


@pytest.mark.parametrize(("token", "is_accepted"), [(OLD, True), (OTHER, False)])
def test_twilio_callbacks_signed_with_the_previous_token(
    token: str, is_accepted: bool
) -> None:
    business_id = BusinessId("business_fd43b272-3035-4a74-a29f-96b1631dd8b5")
    adapter = TwilioCallFallbackAdapter(
        build_settings(
            TWILIO_ACCOUNT_SID="AC" + "0" * 32,
            TWILIO_AUTH_TOKEN="the-current-auth-token-0000",
            TWILIO_AUTH_TOKEN_PREVIOUS=OLD,
            TWILIO_FROM_NUMBER="+15005550006",
        ),
        InMemoryRateLimitBucketAdapter(),
    )
    pairs = [
        ("CallSid", "CA" + "0" * 32),
        ("From", "+995599000000"),
        ("To", "+995322000000"),
    ]
    url = APP_BASE_URL + build_voice_fallback_path(business_id)
    message = url + "".join(name + value for name, value in sorted(pairs))
    signature = base64.b64encode(
        hmac.new(token.encode(), message.encode(), hashlib.sha1).digest()
    ).decode()
    request = CallFallbackWebhookRequest(
        business_id=business_id,
        body=urlencode(pairs).encode(),
        signature_header=WebhookSignatureHeader(signature),
    )

    if is_accepted:
        assert adapter.read_fallback(request, Microseconds(0)).caller_number is not None
    else:
        with pytest.raises(AuthenticationRequiredError):
            adapter.read_fallback(request, Microseconds(0))


@pytest.mark.parametrize(("key", "is_accepted"), [(OLD, True), (OTHER, False)])
def test_flitt_callbacks_signed_with_the_previous_key(
    key: str, is_accepted: bool
) -> None:
    client = FlittClient(
        merchant_id=PlatformIdentifier("1700001"),
        secret_key=PlatformSecret("the-current-flitt-key-0000"),
        previous_secret_key=PlatformSecret(OLD),
    )
    parameters: dict[str, object] = {
        "merchant_id": "1700001",
        "order_id": "order_1",
        "order_status": "approved",
    }
    body = urlencode(
        {**parameters, "signature": build_parameter_signature(key, parameters)}
    )

    if is_accepted:
        verified = client.verify_callback(body, "application/x-www-form-urlencoded")
        assert verified["order_id"] == "order_1"
    else:
        with pytest.raises(AccessDeniedError):
            client.verify_callback(body, "application/x-www-form-urlencoded")
