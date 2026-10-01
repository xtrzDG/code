"""Webhook secrets and signatures of messaging and voice platforms.

All comparisons are constant-time (`hmac.compare_digest`). Derived secrets
are deterministic, so nothing extra is stored: the Telegram secret comes from
the bot token and the platform encryption key, the voice tool secret from the
ElevenLabs webhook secret and the business id.
"""

import hashlib
import hmac

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    TelegramWebhookSecret,
    VoiceToolSecret,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    PresentedWebhookSecret,
    WebhookSignatureHeader,
)
from app.schemas.typings.platform.strings import PlatformSecret

SHA256_SIGNATURE_PREFIX: str = "sha256="
ELEVENLABS_TIMESTAMP_PREFIX: str = "t="
ELEVENLABS_SIGNATURE_PREFIX: str = "v0="
# ElevenLabs signs "<timestamp>.<body>" and rejects deliveries older than this.
ELEVENLABS_SIGNATURE_TOLERANCE_SECONDS: int = 30 * 60
TELEGRAM_SECRET_CONTEXT: bytes = b"assistant-workshop/telegram-webhook/v1\x00"
VOICE_TOOL_SECRET_CONTEXT: bytes = b"assistant-workshop/voice-tools/v1\x00"


def derive_telegram_webhook_secret(
    encryption_key: PlatformSecret,
    bot_token: ChannelSecret | PlatformSecret,
) -> TelegramWebhookSecret:
    """
    Secret registered with setWebhook and repeated by Telegram in
    X-Telegram-Bot-Api-Secret-Token: HMAC-SHA256 of the bot token keyed with
    the platform encryption key, as hex (Telegram allows [A-Za-z0-9_-]).
    """

    digest: str = hmac.new(
        str(encryption_key).encode("utf-8"),
        TELEGRAM_SECRET_CONTEXT + str(bot_token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return TelegramWebhookSecret(digest)


def derive_voice_tool_secret(
    webhook_secret: PlatformSecret,
    business_id: BusinessId,
) -> VoiceToolSecret:
    """
    Per-business secret of the voice-agent webhooks: HMAC-SHA256 of the
    business id keyed with ELEVENLABS_WEBHOOK_SECRET, as hex. A leaked agent
    configuration exposes one business only.
    """

    digest: str = hmac.new(
        str(webhook_secret).encode("utf-8"),
        VOICE_TOOL_SECRET_CONTEXT + str(business_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return VoiceToolSecret(digest)


def sign_body(secret: str, body: bytes) -> str:
    """Hex HMAC-SHA256 of a raw body."""

    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def is_matching_secret(
    expected: str,
    presented: PresentedWebhookSecret | WebhookSignatureHeader | None,
) -> bool:
    """Constant-time equality of a presented secret with the expected one."""

    if presented is None:
        return False

    return hmac.compare_digest(
        expected.encode("utf-8"),
        str(presented).encode("utf-8"),
    )


def is_valid_sha256_signature(
    secret: str,
    body: bytes,
    signature_header: WebhookSignatureHeader | None,
) -> bool:
    """
    Check a "sha256=<hex HMAC-SHA256 of the raw body>" header (Meta
    X-Hub-Signature-256, the voice tool body signature).
    """

    if signature_header is None:
        return False

    header_text: str = str(signature_header).strip()
    if not header_text.lower().startswith(SHA256_SIGNATURE_PREFIX):
        return False

    presented_digest: str = header_text[len(SHA256_SIGNATURE_PREFIX) :].lower()
    return hmac.compare_digest(
        sign_body(secret, body).encode("ascii"),
        presented_digest.encode("utf-8"),
    )


def read_elevenlabs_signature(
    signature_header: WebhookSignatureHeader | None,
) -> tuple[int, str] | None:
    """Timestamp and v0 signature of "t=<unix seconds>,v0=<hex>"."""

    if signature_header is None:
        return None

    timestamp: int | None = None
    signature: str | None = None
    for part in str(signature_header).split(","):
        item: str = part.strip()
        if item.startswith(ELEVENLABS_TIMESTAMP_PREFIX):
            timestamp_text: str = item[len(ELEVENLABS_TIMESTAMP_PREFIX) :]
            if timestamp_text.isascii() and timestamp_text.isdigit():
                timestamp = int(timestamp_text)
        elif item.startswith(ELEVENLABS_SIGNATURE_PREFIX):
            signature = item[len(ELEVENLABS_SIGNATURE_PREFIX) :]

    if timestamp is None or signature is None or signature == "":
        return None

    return timestamp, signature


def is_valid_elevenlabs_signature(
    webhook_secret: PlatformSecret,
    body: bytes,
    signature_header: WebhookSignatureHeader | None,
    now_unix_seconds: int,
) -> bool:
    """
    Check an ElevenLabs-Signature header: HMAC-SHA256 of "<t>.<raw body>"
    keyed with the webhook secret, and a timestamp at most 30 minutes away
    from now (older deliveries could be replays).
    """

    parsed_signature: tuple[int, str] | None = read_elevenlabs_signature(
        signature_header
    )
    if parsed_signature is None:
        return False

    timestamp, presented_digest = parsed_signature
    if abs(now_unix_seconds - timestamp) > ELEVENLABS_SIGNATURE_TOLERANCE_SECONDS:
        return False

    signed_message: bytes = str(timestamp).encode("ascii") + b"." + body
    expected_digest: str = hmac.new(
        str(webhook_secret).encode("utf-8"),
        signed_message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(
        expected_digest.encode("ascii"),
        presented_digest.lower().encode("utf-8"),
    )
