"""
The providers' webhook addresses and what a delivery to each must carry
before its body is read: the provider's signature or secret header in its
exact shape. Whether the signature is right, and whether a timed one is
fresh (ElevenLabs, Stripe), is checked by the route's own verifier with
the platform's clock, after the body (within its route's limit) is read;
these checks only refuse what can never be right, without reading
anything.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.adapters.payments.flitt_payment_gateway_adapter import FLITT_WEBHOOK_PATH
from app.adapters.payments.stripe_billing_adapter import STRIPE_WEBHOOK_PATH
from app.gateways.http.telephony_routes import (
    ZADARMA_NOTIFICATIONS_PATH,
    ZADARMA_SIGNATURE_HEADER,
)
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.utilities.calls.twilio_voice_webhooks import (
    TWILIO_FALLBACK_DIAL_PATH_TEMPLATE,
    TWILIO_SIGNATURE_HEADER,
    TWILIO_VOICE_FALLBACK_PATH_TEMPLATE,
)
from app.utilities.channels.channel_endpoints import (
    ELEVENLABS_SIGNATURE_HEADER,
    META_SIGNATURE_HEADER,
    META_WEBHOOK_PATH,
    TELEGRAM_PLATFORM_WEBHOOK_PATH,
    TELEGRAM_SECRET_HEADER,
    TELEGRAM_WEBHOOK_PATH_TEMPLATE,
    VOICE_BODY_SIGNATURE_HEADER,
    VOICE_BUSINESS_ID_HEADER,
    VOICE_CALL_INITIATION_PATH,
    VOICE_POST_CALL_PATH,
    VOICE_TOOL_PATH_TEMPLATE,
    VOICE_TOOL_SECRET_HEADER,
)
from app.utilities.channels.webhook_signatures import read_elevenlabs_signature

# A header check of the request's headers (lower-case names): the refusal
# reason, or None when the delivery may be read.
type DeliveryCheck = Callable[[Mapping[str, str]], str | None]

MISSING_SIGNATURE: str = "missing_signature"
MALFORMED_SIGNATURE: str = "malformed_signature"
STRIPE_SIGNATURE_HEADER: str = "stripe-signature"

HEX_SHA256: re.Pattern[str] = re.compile(r"[0-9a-fA-F]{64}")
SHA256_HEADER: re.Pattern[str] = re.compile(r"sha256=[0-9a-fA-F]{64}")
# Telegram allows 1-256 characters of [A-Za-z0-9_-] for a secret token.
TELEGRAM_SECRET: re.Pattern[str] = re.compile(r"[A-Za-z0-9_-]{1,256}")
# Base64 of an HMAC-SHA1 (raw: 28, of the hex digest: 56) or SHA-256 (44).
BASE64_DIGEST: re.Pattern[str] = re.compile(r"[A-Za-z0-9+/]{20,100}={0,2}")
STRIPE_TIMESTAMP: re.Pattern[str] = re.compile(r"(?:^|,)\s*t=[0-9]{1,12}\s*(?:,|$)")
STRIPE_V1: re.Pattern[str] = re.compile(r"(?:^|,)\s*v1=[0-9a-fA-F]{64}\s*(?:,|$)")


def template_pattern(template: str) -> re.Pattern[str]:
    """A route template ("/v1/x/{id}/y") as an exact path pattern."""

    escaped: str = re.escape(template)
    return re.compile("^" + re.sub(r"\\\{[a-z_]+\\\}", "[^/]+", escaped) + "$")


def require_matching(header: str, pattern: re.Pattern[str]) -> DeliveryCheck:
    def check(headers: Mapping[str, str]) -> str | None:
        value: str | None = headers.get(header.lower())
        if value is None or value.strip() == "":
            return MISSING_SIGNATURE

        return None if pattern.fullmatch(value.strip()) else MALFORMED_SIGNATURE

    return check


def check_elevenlabs_signature(headers: Mapping[str, str]) -> str | None:
    raw: str | None = headers.get(ELEVENLABS_SIGNATURE_HEADER.lower())
    if raw is None or raw.strip() == "":
        return MISSING_SIGNATURE

    parsed: tuple[int, str] | None = read_elevenlabs_signature(
        WebhookSignatureHeader(raw)
    )
    if parsed is None or not HEX_SHA256.fullmatch(parsed[1]):
        return MALFORMED_SIGNATURE

    return None


def check_voice_agent_credentials(headers: Mapping[str, str]) -> str | None:
    """The business id and its tool secret or body signature (sha256=)."""

    if headers.get(VOICE_BUSINESS_ID_HEADER.lower(), "").strip() == "":
        return MISSING_SIGNATURE

    signature: str | None = headers.get(VOICE_BODY_SIGNATURE_HEADER.lower())
    if signature is not None:
        is_well_formed: bool = SHA256_HEADER.fullmatch(signature.strip()) is not None
        return None if is_well_formed else MALFORMED_SIGNATURE

    secret: str | None = headers.get(VOICE_TOOL_SECRET_HEADER.lower())
    if secret is None or secret.strip() == "":
        return MISSING_SIGNATURE

    return None if HEX_SHA256.fullmatch(secret.strip()) else MALFORMED_SIGNATURE


def check_stripe_signature(headers: Mapping[str, str]) -> str | None:
    """`t=<unix seconds>` and at least one `v1=<hex HMAC-SHA256>`."""

    raw: str | None = headers.get(STRIPE_SIGNATURE_HEADER)
    if raw is None or raw.strip() == "":
        return MISSING_SIGNATURE

    if STRIPE_TIMESTAMP.search(raw) is None or STRIPE_V1.search(raw) is None:
        return MALFORMED_SIGNATURE

    return None


def accept_without_header(headers: Mapping[str, str]) -> str | None:
    """Flitt signs inside the body: only its route's verifier can tell."""

    del headers
    return None


@dataclass(frozen=True)
class WebhookRoute:
    """
    One provider's webhook address: `provider` and `path` name it in the
    security log, `check` runs on POST, `per_minute` is the flood budget of
    one client network, and `refusal_status` is what the route's own
    verifier answers to a wrong signature (the same for both refusals).
    """

    provider: str
    path: str
    check: DeliveryCheck
    per_minute: int
    refusal_status: int = 401

    @property
    def pattern(self) -> re.Pattern[str]:
        return template_pattern(self.path)


# Platforms deliver in bursts from few addresses: the budgets leave room
# for a busy hour's peak and stop a script that floods one address.
WEBHOOK_ROUTES: tuple[WebhookRoute, ...] = (
    WebhookRoute(
        "telegram",
        TELEGRAM_WEBHOOK_PATH_TEMPLATE,
        require_matching(TELEGRAM_SECRET_HEADER, TELEGRAM_SECRET),
        per_minute=1_200,
    ),
    WebhookRoute(
        "telegram_platform",
        TELEGRAM_PLATFORM_WEBHOOK_PATH,
        require_matching(TELEGRAM_SECRET_HEADER, TELEGRAM_SECRET),
        per_minute=600,
    ),
    WebhookRoute(
        "meta",
        META_WEBHOOK_PATH,
        require_matching(META_SIGNATURE_HEADER, SHA256_HEADER),
        per_minute=1_200,
    ),
    WebhookRoute(
        "elevenlabs",
        VOICE_POST_CALL_PATH,
        check_elevenlabs_signature,
        per_minute=300,
    ),
    WebhookRoute(
        "elevenlabs_agent",
        VOICE_CALL_INITIATION_PATH,
        check_voice_agent_credentials,
        per_minute=600,
    ),
    WebhookRoute(
        "elevenlabs_agent",
        VOICE_TOOL_PATH_TEMPLATE,
        check_voice_agent_credentials,
        per_minute=1_200,
    ),
    WebhookRoute(
        "zadarma",
        ZADARMA_NOTIFICATIONS_PATH,
        require_matching(ZADARMA_SIGNATURE_HEADER, BASE64_DIGEST),
        per_minute=300,
    ),
    WebhookRoute(
        "twilio",
        TWILIO_VOICE_FALLBACK_PATH_TEMPLATE,
        require_matching(TWILIO_SIGNATURE_HEADER, BASE64_DIGEST),
        per_minute=300,
    ),
    WebhookRoute(
        "twilio",
        TWILIO_FALLBACK_DIAL_PATH_TEMPLATE,
        require_matching(TWILIO_SIGNATURE_HEADER, BASE64_DIGEST),
        per_minute=300,
    ),
    WebhookRoute(
        "stripe",
        STRIPE_WEBHOOK_PATH,
        check_stripe_signature,
        per_minute=300,
        refusal_status=403,
    ),
    WebhookRoute("flitt", FLITT_WEBHOOK_PATH, accept_without_header, per_minute=300),
)
WEBHOOK_PATH_PREFIXES: tuple[str, ...] = (
    "/v1/channels/",
    "/v1/voice/",
    "/v1/telephony/",
    "/v1/payments/",
)
COMPILED_WEBHOOK_ROUTES: tuple[tuple[re.Pattern[str], WebhookRoute], ...] = tuple(
    (route.pattern, route) for route in WEBHOOK_ROUTES
)


def find_webhook_route(path: str) -> WebhookRoute | None:
    """The provider address `path` is, if it is one."""

    if not path.startswith(WEBHOOK_PATH_PREFIXES):
        return None

    for pattern, route in COMPILED_WEBHOOK_ROUTES:
        if pattern.match(path):
            return route

    return None
