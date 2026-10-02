import hashlib
import time
from collections.abc import Callable

import httpx
from cryptography.hazmat.primitives.asymmetric import ec

from app.clients.webpush.push_encryption import (
    decode_base64url,
    encode_base64url,
    encrypt_push_payload,
    new_salt,
    new_sender_key,
)
from app.clients.webpush.vapid import (
    check_vapid_key_pair,
    load_vapid_private_key,
    push_service_origin,
    sign_vapid_token,
    vapid_authorization,
)
from app.contracts.notification_clients import WebPushClientContract
from app.schemas.dto.notifications.web_push import WebPushMessage
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
)
from app.schemas.exceptions.notification_errors import PushSubscriptionGoneError
from app.schemas.typings.notifications.constrained_strings import (
    VapidPublicKey,
    VapidSubject,
)
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.platform.strings import PlatformSecret

REQUEST_TIMEOUT_SECONDS: float = 10.0
GONE_STATUSES: frozenset[int] = frozenset({403, 404, 410})
# A Topic header is at most 32 base64url characters (RFC 8030, 5.4).
TOPIC_DIGEST_BYTES: int = 24


class WebPushClient(WebPushClientContract):
    """
    Web Push with VAPID (RFC 8030, 8291, 8292): each message is encrypted
    for the browser's keys with a fresh ephemeral key and salt, and posted
    to the subscription's push service with a VAPID token for that
    service's origin. The key pair is checked when the client is built.

    Errors name the push service's status, never the endpoint (it
    identifies a device) or the payload.
    """

    def __init__(
        self,
        private_key: PlatformSecret,
        public_key: VapidPublicKey,
        subject: VapidSubject,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.time,
        sender_key_factory: Callable[[], ec.EllipticCurvePrivateKey] = new_sender_key,
        salt_factory: Callable[[], bytes] = new_salt,
    ) -> None:
        self._private_key: ec.EllipticCurvePrivateKey = load_vapid_private_key(
            str(private_key)
        )
        check_vapid_key_pair(self._private_key, str(public_key))
        self._public_key: VapidPublicKey = public_key
        self._subject: VapidSubject = subject
        self._clock: Callable[[], float] = clock
        self._sender_key_factory: Callable[[], ec.EllipticCurvePrivateKey] = (
            sender_key_factory
        )
        self._salt_factory: Callable[[], bytes] = salt_factory
        self._http_client: httpx.Client = httpx.Client(
            timeout=REQUEST_TIMEOUT_SECONDS, transport=transport
        )

    @property
    def public_key(self) -> VapidPublicKey:
        return self._public_key

    def send(self, message: WebPushMessage) -> None:
        try:
            body: bytes = encrypt_push_payload(
                str(message.payload).encode("utf-8"),
                decode_base64url(str(message.p256dh)),
                decode_base64url(str(message.auth)),
                self._sender_key_factory(),
                self._salt_factory(),
            )
        except ValueError as error:
            raise PushSubscriptionGoneError(
                f"The device subscription cannot be encrypted for: {error}"
            ) from None

        try:
            response: httpx.Response = self._http_client.post(
                str(message.endpoint),
                content=body,
                headers=self._headers(message),
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"The push service could not be reached: {type(error).__name__}."
            ) from None

        raise_for_push_status(response)

    def _headers(self, message: WebPushMessage) -> dict[str, str]:
        token: str = sign_vapid_token(
            self._private_key,
            push_service_origin(str(message.endpoint)),
            str(self._subject),
            int(self._clock()),
        )
        headers: dict[str, str] = {
            "Authorization": vapid_authorization(token, str(self._public_key)),
            "Content-Encoding": "aes128gcm",
            "Content-Type": "application/octet-stream",
            "TTL": str(int(message.time_to_live_seconds)),
            "Urgency": message.urgency.value,
        }
        if message.topic is not None:
            headers["Topic"] = push_topic(str(message.topic))

        return headers


def push_topic(tag: str) -> str:
    """A Topic header for a notification tag (32 base64url characters)."""

    return encode_base64url(hashlib.sha256(tag.encode()).digest()[:TOPIC_DIGEST_BYTES])


def raise_for_push_status(response: httpx.Response) -> None:
    """Accepted (2xx) passes; anything else raises the error it means."""

    status: int = response.status_code
    if 200 <= status < 300:
        return

    if status in GONE_STATUSES:
        raise PushSubscriptionGoneError(
            f"The push service no longer knows this device (HTTP {status})."
        )

    if status == 429:
        raise ProviderRateLimitedError(
            "The push service asked to slow down (HTTP 429).",
            retry_after_seconds=read_retry_after(response),
        )

    if status >= 500:
        raise ExternalServiceError(f"The push service failed (HTTP {status}).")

    raise ProviderRejectedMessageError(
        f"The push service refused the notification (HTTP {status})."
    )


def read_retry_after(response: httpx.Response) -> RetryAfterSeconds | None:
    raw_value: str = response.headers.get("Retry-After", "").strip()
    if not raw_value.isdigit():
        return None

    seconds: int = int(raw_value)
    if seconds < 1:
        return None

    return RetryAfterSeconds(min(seconds, 24 * 60 * 60))
