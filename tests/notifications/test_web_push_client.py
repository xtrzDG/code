"""The Web Push client: headers, encryption hand-off and status classes."""

import httpx
import pytest

from app.clients.webpush.push_encryption import decode_base64url
from app.clients.webpush.vapid import load_vapid_private_key
from app.clients.webpush.web_push_client import WebPushClient, push_topic
from app.schemas.constants.notifications import WebPushUrgency
from app.schemas.dto.notifications.web_push import WebPushMessage
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
)
from app.schemas.exceptions.notification_errors import PushSubscriptionGoneError
from app.schemas.typings.notifications.constrained_integers import (
    PushTimeToLiveSeconds,
)
from app.schemas.typings.notifications.constrained_strings import (
    PushAuthSecret,
    PushEndpointUrl,
    PushNotificationTag,
    PushPublicKey,
    VapidPublicKey,
    VapidSubject,
)
from app.schemas.typings.notifications.strings import PushPayloadJson
from app.schemas.typings.platform.strings import PlatformSecret
from tests.notifications.test_web_push_encryption import (
    AUTH_SECRET,
    EXPECTED_BODY,
    PLAINTEXT,
    RECEIVER_PUBLIC,
    SALT,
    SENDER_PRIVATE,
    SENDER_PUBLIC,
)

ENDPOINT: str = "https://fcm.googleapis.com/fcm/send/device-1"


def build_client(
    handler: httpx.MockTransport,
) -> WebPushClient:
    return WebPushClient(
        private_key=PlatformSecret(SENDER_PRIVATE),
        public_key=VapidPublicKey(SENDER_PUBLIC),
        subject=VapidSubject("mailto:ops@example.com"),
        transport=handler,
        clock=lambda: 1_790_000_000.0,
        sender_key_factory=lambda: load_vapid_private_key(SENDER_PRIVATE),
        salt_factory=lambda: decode_base64url(SALT),
    )


def message(tag: str | None = "handoff:h1") -> WebPushMessage:
    return WebPushMessage(
        endpoint=PushEndpointUrl(ENDPOINT),
        p256dh=PushPublicKey(RECEIVER_PUBLIC),
        auth=PushAuthSecret(AUTH_SECRET),
        payload=PushPayloadJson(PLAINTEXT.decode()),
        time_to_live_seconds=PushTimeToLiveSeconds(86_400),
        urgency=WebPushUrgency.HIGH,
        topic=None if tag is None else PushNotificationTag(tag),
    )


def test_a_message_is_posted_encrypted_with_vapid_and_its_headers() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201)

    client = build_client(httpx.MockTransport(handle))
    client.send(message())

    [request] = requests
    assert str(request.url) == ENDPOINT
    assert request.content == decode_base64url(EXPECTED_BODY)
    assert request.headers["content-encoding"] == "aes128gcm"
    assert request.headers["ttl"] == "86400"
    assert request.headers["urgency"] == "high"
    assert request.headers["topic"] == push_topic("handoff:h1")
    assert len(request.headers["topic"]) == 32
    assert request.headers["authorization"].startswith("vapid t=ey")
    assert request.headers["authorization"].endswith(f", k={SENDER_PUBLIC}")
    assert client.public_key == SENDER_PUBLIC


def test_no_topic_without_a_tag() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    build_client(httpx.MockTransport(handle)).send(message(tag=None))

    assert "topic" not in requests[0].headers


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (404, PushSubscriptionGoneError),
        (410, PushSubscriptionGoneError),
        (403, PushSubscriptionGoneError),
        (429, ProviderRateLimitedError),
        (400, ProviderRejectedMessageError),
        (413, ProviderRejectedMessageError),
        (502, ExternalServiceError),
    ],
)
def test_push_service_answers_become_delivery_errors(
    status: int, error_type: type[Exception]
) -> None:
    client = build_client(
        httpx.MockTransport(
            lambda request: httpx.Response(status, headers={"Retry-After": "30"})
        )
    )

    with pytest.raises(error_type) as raised:
        client.send(message())

    assert ENDPOINT not in str(raised.value)
    if isinstance(raised.value, ProviderRateLimitedError):
        assert raised.value.retry_after_seconds == 30


def test_odd_retry_after_values_are_ignored() -> None:
    for value in ("soon", "0", ""):
        client = build_client(
            httpx.MockTransport(
                lambda request, value=value: httpx.Response(
                    429, headers={"Retry-After": value}
                )
            )
        )
        with pytest.raises(ProviderRateLimitedError) as raised:
            client.send(message())

        assert raised.value.retry_after_seconds is None


def test_network_failures_may_pass_on_another_try() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(ExternalServiceError, match="ConnectError"):
        build_client(httpx.MockTransport(fail)).send(message())


def test_a_subscription_that_cannot_be_encrypted_for_is_gone() -> None:
    client = build_client(httpx.MockTransport(lambda request: httpx.Response(201)))
    broken = message().model_copy(update={"auth": PushAuthSecret("c2hvcnRzaG9ydHNo")})

    with pytest.raises(PushSubscriptionGoneError):
        client.send(broken)


def test_a_mismatched_key_pair_stops_the_client() -> None:
    with pytest.raises(ValueError):
        WebPushClient(
            private_key=PlatformSecret(SENDER_PRIVATE),
            public_key=VapidPublicKey(RECEIVER_PUBLIC),
            subject=VapidSubject("mailto:ops@example.com"),
        )
