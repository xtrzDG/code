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
from app.utilities.config_helpers.secret_rotation import accepted_secrets


def require_voice_webhook_access(
    webhook_secret: PlatformSecret | None,
    credentials: VoiceWebhookCredentials,
    body: bytes,
    previous_webhook_secret: PlatformSecret | None = None,
) -> None:
    """
    Accept a request of the business named in the credentials when it is
    signed with the business's tool secret (HMAC-SHA256 of the raw body,
    "sha256=<hex>") or, without a signature, presents that secret. The tool
    secret derives from ELEVENLABS_WEBHOOK_SECRET; while a rotation is under
    way, agents still carry the one derived from the previous value
    (ELEVENLABS_WEBHOOK_SECRET_PREVIOUS), which is accepted too. Raises
    AuthenticationRequiredError otherwise; all comparisons are constant-time.
    """

    webhook_secrets: list[PlatformSecret] = accepted_secrets(
        webhook_secret, previous_webhook_secret
    )
    if not webhook_secrets:
        raise AuthenticationRequiredError("Voice webhooks are not configured.")

    tool_secrets: list[VoiceToolSecret] = [
        derive_voice_tool_secret(secret, credentials.business_id)
        for secret in webhook_secrets
    ]
    if credentials.body_signature is not None:
        if any(
            is_valid_sha256_signature(
                str(tool_secret), body, credentials.body_signature
            )
            for tool_secret in tool_secrets
        ):
            return

        raise AuthenticationRequiredError("The voice webhook signature is wrong.")

    if not any(
        is_matching_secret(str(tool_secret), credentials.tool_secret)
        for tool_secret in tool_secrets
    ):
        raise AuthenticationRequiredError(
            "The voice webhook secret is missing or wrong."
        )
