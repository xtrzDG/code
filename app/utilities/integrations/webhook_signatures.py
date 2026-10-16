"""
Signatures of webhook requests: `Workshop-Signature: t=<unix seconds>,v1=<hex>`
where the hex is HMAC-SHA256 of `<t>.<body>` keyed with the endpoint's
signing secret. A receiver recomputes it over the raw body, compares in
constant time and refuses a `t` older than five minutes (replays).
"""

import hashlib
import hmac

from app.schemas.typings.integrations.constrained_strings import (
    WebhookSignature,
    WebhookSigningSecret,
)
from app.schemas.typings.integrations.strings import WebhookPayloadJson

SIGNATURE_HEADER: str = "Workshop-Signature"
EVENT_ID_HEADER: str = "Workshop-Event-Id"
EVENT_TYPE_HEADER: str = "Workshop-Event-Type"
DELIVERY_ID_HEADER: str = "Workshop-Delivery-Id"


def sign_webhook_body(
    secret: WebhookSigningSecret, signed_at_seconds: int, body: WebhookPayloadJson
) -> WebhookSignature:
    """The header value for `body` signed at `signed_at_seconds`."""

    digest: str = _digest(secret, signed_at_seconds, str(body))
    return WebhookSignature(f"t={signed_at_seconds},v1={digest}")


def _digest(secret: WebhookSigningSecret, signed_at_seconds: int, body: str) -> str:
    message: bytes = f"{signed_at_seconds}.{body}".encode()
    return hmac.new(str(secret).encode(), message, hashlib.sha256).hexdigest()
