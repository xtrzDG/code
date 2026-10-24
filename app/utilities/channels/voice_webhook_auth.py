"""Authentication of the voice agent's webhooks (tools, call initiation)."""

from app.schemas.dto.voice_webhooks import VoiceWebhookCredentials
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.channels.constrained_strings import VoiceToolSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import (
    derive_voice_tool_secret,
    is_matching_secret,
    is_valid_sha256_signature,
)


def require_voice_webhook_access(
    webhook_secret: PlatformSecret | None,
    credentials: VoiceWebhookCredentials,
    body: bytes,
) -> None:
    """
    Accept a request of the business named in the credentials when it is
    signed with the business's tool secret (HMAC-SHA256 of the raw body,
    "sha256=<hex>") or, without a signature, presents that secret. Raises
    AuthenticationRequiredError otherwise; all comparisons are constant-time.
    """

    if webhook_secret is None:
        raise AuthenticationRequiredError("Voice webhooks are not configured.")

    tool_secret: VoiceToolSecret = derive_voice_tool_secret(
        webhook_secret,
        credentials.business_id,
    )
    if credentials.body_signature is not None:
        if is_valid_sha256_signature(
            str(tool_secret),
            body,
            credentials.body_signature,
        ):
            return

        raise AuthenticationRequiredError("The voice webhook signature is wrong.")

    if not is_matching_secret(str(tool_secret), credentials.tool_secret):
        raise AuthenticationRequiredError(
            "The voice webhook secret is missing or wrong."
        )
