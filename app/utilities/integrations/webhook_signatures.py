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
# A receiver should refuse signatures older than this (replays).
SIGNATURE_TOLERANCE_SECONDS: int = 5 * 60


def sign_webhook_body(
    secret: WebhookSigningSecret, signed_at_seconds: int, body: WebhookPayloadJson
) -> WebhookSignature:
    """The header value for `body` signed at `signed_at_seconds`."""

    digest: str = _digest(secret, signed_at_seconds, str(body))
    return WebhookSignature(f"t={signed_at_seconds},v1={digest}")


def is_valid_webhook_signature(
    secret: WebhookSigningSecret,
    header: str,
    body: str,
    now_seconds: int,
    tolerance_seconds: int = SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    """
    What a receiver checks: the header is well formed, its time is within
    the tolerance of `now_seconds` and its digest matches the body.
    """

    parts: dict[str, str] = {}
    for item in header.split(","):
        name, separator, value = item.strip().partition("=")
        if separator:
            parts[name] = value

    signed_at: str = parts.get("t", "")
    expected: str = parts.get("v1", "")
    if not signed_at.isdigit() or expected == "":
        return False

    if abs(now_seconds - int(signed_at)) > tolerance_seconds:
        return False

    return hmac.compare_digest(_digest(secret, int(signed_at), body), expected)


def _digest(secret: WebhookSigningSecret, signed_at_seconds: int, body: str) -> str:
    message: bytes = f"{signed_at_seconds}.{body}".encode()
    return hmac.new(str(secret).encode(), message, hashlib.sha256).hexdigest()
