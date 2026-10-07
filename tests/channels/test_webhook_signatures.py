import hashlib
import hmac

import pytest

from app.schemas.dto.voice_webhooks import VoiceWebhookCredentials
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    PresentedWebhookSecret,
    WebhookSignatureHeader,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.voice_webhook_auth import require_voice_webhook_access
from app.utilities.channels.webhook_signatures import (
    ELEVENLABS_SIGNATURE_TOLERANCE_SECONDS,
    derive_telegram_webhook_secret,
    derive_voice_tool_secret,
    is_matching_secret,
    is_valid_elevenlabs_signature,
    is_valid_sha256_signature,
    read_elevenlabs_signature,
    sign_body,
)
from tests.channels.channels_payloads import sign_elevenlabs, sign_meta
from tests.channels.channels_settings import ELEVENLABS_WEBHOOK_SECRET

BODY: bytes = '{"text":"გამარჯობა, שלום"}'.encode()
NOW: int = 1_790_856_000
KEY = PlatformSecret("platform-encryption-key-0123456789")


def test_telegram_secret_is_deterministic_per_token_and_key() -> None:
    first = derive_telegram_webhook_secret(KEY, ChannelSecret("1:token-a"))
    again = derive_telegram_webhook_secret(KEY, ChannelSecret("1:token-a"))
    other_token = derive_telegram_webhook_secret(KEY, ChannelSecret("1:token-b"))
    other_key = derive_telegram_webhook_secret(
        PlatformSecret("another-key-0123456789"), ChannelSecret("1:token-a")
    )

    assert first == again
    assert len({first, other_token, other_key}) == 3
    assert str(first).isalnum() and len(first) == 64
    assert "token" not in first


def test_voice_tool_secret_differs_per_business() -> None:
    secret = PlatformSecret(ELEVENLABS_WEBHOOK_SECRET)
    business_a, business_b = BusinessId(), BusinessId()

    assert derive_voice_tool_secret(secret, business_a) == derive_voice_tool_secret(
        secret, business_a
    )
    assert derive_voice_tool_secret(secret, business_a) != derive_voice_tool_secret(
        secret, business_b
    )


@pytest.mark.parametrize(
    ("presented", "expected"),
    [("abc", True), ("abd", False), ("", False), (None, False), ("abcd", False)],
)
def test_secret_comparison(presented: str | None, expected: bool) -> None:
    assert (
        is_matching_secret(
            "abc", None if presented is None else PresentedWebhookSecret(presented)
        )
        is expected
    )


def test_sha256_signature_accepts_only_the_exact_body() -> None:
    header = WebhookSignatureHeader(sign_meta(BODY, "secret"))
    uppercase = WebhookSignatureHeader("SHA256=" + sign_body("secret", BODY).upper())

    assert is_valid_sha256_signature("secret", BODY, header)
    assert is_valid_sha256_signature("secret", BODY, uppercase)
    assert not is_valid_sha256_signature("secret", BODY + b" ", header)
    assert not is_valid_sha256_signature("other", BODY, header)
    assert not is_valid_sha256_signature("secret", BODY, None)
    assert not is_valid_sha256_signature(
        "secret", BODY, WebhookSignatureHeader(sign_body("secret", BODY))
    )
    assert not is_valid_sha256_signature(
        "secret", BODY, WebhookSignatureHeader("sha256=ünïcode")
    )


def test_elevenlabs_signature_header_parsing() -> None:
    assert read_elevenlabs_signature(WebhookSignatureHeader("t=10,v0=ab")) == (
        10,
        "ab",
    )
    assert read_elevenlabs_signature(WebhookSignatureHeader("v0=ab, t=10")) == (
        10,
        "ab",
    )
    for broken in ("t=10", "v0=ab", "t=x,v0=ab", "t=10,v0=", "", "t=١٠,v0=ab"):
        assert read_elevenlabs_signature(WebhookSignatureHeader(broken)) is None

    assert read_elevenlabs_signature(None) is None


def test_elevenlabs_signature_valid_wrong_and_stale() -> None:
    secret = PlatformSecret(ELEVENLABS_WEBHOOK_SECRET)
    header = WebhookSignatureHeader(sign_elevenlabs(BODY, NOW))

    assert is_valid_elevenlabs_signature(secret, BODY, header, NOW)
    assert is_valid_elevenlabs_signature(secret, BODY, header, NOW + 60)
    assert not is_valid_elevenlabs_signature(secret, BODY + b"x", header, NOW)
    assert not is_valid_elevenlabs_signature(
        PlatformSecret("other-secret"), BODY, header, NOW
    )
    stale_now: int = NOW + ELEVENLABS_SIGNATURE_TOLERANCE_SECONDS + 1
    assert not is_valid_elevenlabs_signature(secret, BODY, header, stale_now)
    future_now: int = NOW - ELEVENLABS_SIGNATURE_TOLERANCE_SECONDS - 1
    assert not is_valid_elevenlabs_signature(secret, BODY, header, future_now)
    assert not is_valid_elevenlabs_signature(secret, BODY, None, NOW)


def test_elevenlabs_signature_matches_the_sdk_algorithm() -> None:
    # The SDK signs f"{timestamp}.{raw_body}" with the secret as UTF-8.
    digest: str = hmac.new(
        ELEVENLABS_WEBHOOK_SECRET.encode(),
        f"{NOW}.{BODY.decode()}".encode(),
        hashlib.sha256,
    ).hexdigest()

    assert is_valid_elevenlabs_signature(
        PlatformSecret(ELEVENLABS_WEBHOOK_SECRET),
        BODY,
        WebhookSignatureHeader(f"t={NOW},v0={digest}"),
        NOW,
    )


class TestVoiceWebhookAccess:
    secret = PlatformSecret(ELEVENLABS_WEBHOOK_SECRET)
    business_id = BusinessId()

    def tool_secret(self, business_id: BusinessId | None = None) -> str:
        return str(
            derive_voice_tool_secret(self.secret, business_id or self.business_id)
        )

    def credentials(
        self,
        tool_secret: str | None = None,
        signature: str | None = None,
        business_id: BusinessId | None = None,
    ) -> VoiceWebhookCredentials:
        return VoiceWebhookCredentials(
            business_id=business_id or self.business_id,
            tool_secret=None
            if tool_secret is None
            else PresentedWebhookSecret(tool_secret),
            body_signature=None
            if signature is None
            else WebhookSignatureHeader(signature),
        )

    def test_tool_secret_header_is_accepted(self) -> None:
        require_voice_webhook_access(
            self.secret, self.credentials(tool_secret=self.tool_secret()), BODY
        )

    def test_body_signature_is_accepted(self) -> None:
        signature: str = "sha256=" + sign_body(self.tool_secret(), BODY)
        require_voice_webhook_access(
            self.secret, self.credentials(signature=signature), BODY
        )

    def test_wrong_signature_is_refused_even_with_the_right_secret(self) -> None:
        with pytest.raises(AuthenticationRequiredError):
            require_voice_webhook_access(
                self.secret,
                self.credentials(
                    tool_secret=self.tool_secret(),
                    signature="sha256=" + sign_body("wrong", BODY),
                ),
                BODY,
            )

    def test_secret_of_another_business_is_refused(self) -> None:
        other_business = BusinessId()
        with pytest.raises(AuthenticationRequiredError):
            require_voice_webhook_access(
                self.secret,
                self.credentials(tool_secret=self.tool_secret(other_business)),
                BODY,
            )

    def test_missing_credentials_and_configuration_are_refused(self) -> None:
        with pytest.raises(AuthenticationRequiredError):
            require_voice_webhook_access(self.secret, self.credentials(), BODY)

        with pytest.raises(AuthenticationRequiredError):
            require_voice_webhook_access(
                None, self.credentials(tool_secret=self.tool_secret()), BODY
            )
