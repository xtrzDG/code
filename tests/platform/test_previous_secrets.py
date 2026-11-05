"""
`<NAME>_PREVIOUS`: the old value of a rotated webhook secret, read as an
optional setting, accepted by verifiers after the current one, never alone,
and checked in production only for leftovers and published test values.
"""

import pytest

from app.schemas.dto.voice_webhooks import VoiceWebhookCredentials
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import PresentedWebhookSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.voice_webhook_auth import require_voice_webhook_access
from app.utilities.channels.webhook_signatures import derive_voice_tool_secret
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.secret_rotation import accepted_secrets
from tests.platform.production_settings import problems_with

CURRENT = PlatformSecret("the-current-webhook-secret-0000")  # gitleaks:allow
PREVIOUS = PlatformSecret("the-previous-webhook-secret-000")  # gitleaks:allow
BUSINESS = BusinessId("business_fd43b272-3035-4a74-a29f-96b1631dd8b5")
NAMES: tuple[str, ...] = (
    "ELEVENLABS_WEBHOOK_SECRET",
    "META_APP_SECRET",
    "FLITT_SECRET_KEY",
    "ZADARMA_API_SECRET",
    "TWILIO_AUTH_TOKEN",
)


def test_the_current_value_comes_first_and_the_previous_one_never_alone() -> None:
    assert accepted_secrets(CURRENT, PREVIOUS) == [CURRENT, PREVIOUS]
    assert accepted_secrets(CURRENT, None) == [CURRENT]
    assert accepted_secrets(CURRENT, PlatformSecret(str(CURRENT))) == [CURRENT]
    assert accepted_secrets(None, PREVIOUS) == []


def test_previous_values_are_read_and_kept_out_of_the_settings_repr() -> None:
    settings = assemble_app_settings(
        {"APP_ENV": "test", **{f"{name}_PREVIOUS": f"old-{name}" for name in NAMES}}
    )
    unset = assemble_app_settings({"APP_ENV": "test", "META_APP_SECRET_PREVIOUS": " "})

    previous = settings.previous_secrets
    assert previous.elevenlabs_webhook_secret == "old-ELEVENLABS_WEBHOOK_SECRET"
    assert previous.meta_app_secret == "old-META_APP_SECRET"
    assert previous.flitt_secret_key == "old-FLITT_SECRET_KEY"
    assert previous.zadarma_api_secret == "old-ZADARMA_API_SECRET"
    assert previous.twilio_auth_token == "old-TWILIO_AUTH_TOKEN"
    assert "old-" not in repr(previous)
    assert unset.previous_secrets.meta_app_secret is None


def credentials_of(secret: PlatformSecret) -> VoiceWebhookCredentials:
    return VoiceWebhookCredentials(
        business_id=BUSINESS,
        tool_secret=PresentedWebhookSecret(
            str(derive_voice_tool_secret(secret, BUSINESS))
        ),
    )


def test_agents_set_up_before_the_rotation_keep_calling_their_tools() -> None:
    require_voice_webhook_access(CURRENT, credentials_of(CURRENT), b"{}", PREVIOUS)
    require_voice_webhook_access(CURRENT, credentials_of(PREVIOUS), b"{}", PREVIOUS)

    with pytest.raises(AuthenticationRequiredError):
        require_voice_webhook_access(CURRENT, credentials_of(PREVIOUS), b"{}")
    with pytest.raises(AuthenticationRequiredError, match="not configured"):
        require_voice_webhook_access(None, credentials_of(PREVIOUS), b"{}", PREVIOUS)


def test_production_takes_previous_values_as_optional() -> None:
    rotating = {
        "META_APP_SECRET": "the-new-meta-secret",
        "META_APP_SECRET_PREVIOUS": "old-meta-secret",
    }

    assert problems_with(rotating) == []


@pytest.mark.parametrize("name", NAMES)
def test_production_refuses_a_previous_value_without_the_current_one(name: str) -> None:
    problems = problems_with({name: None, f"{name}_PREVIOUS": "old-value-0000"})

    assert (
        f"{name}_PREVIOUS is set without {name}: a previous value is only accepted "
        f"next to the current one; set {name} or remove {name}_PREVIOUS."
    ) in problems


def test_production_refuses_flitts_published_key_as_the_previous_one() -> None:
    problems = problems_with({"FLITT_SECRET_KEY_PREVIOUS": "test"})

    assert any(
        problem.startswith("FLITT_SECRET_KEY_PREVIOUS is the test")
        for problem in problems
    )
