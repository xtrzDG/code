import pytest
from pydantic import ValidationError

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)


def test_channel_settings_have_safe_defaults() -> None:
    settings = assemble_app_settings({})

    # Voice data stays in the EU by default (concept sections 7 and 10).
    assert settings.elevenlabs_api_base_url == "https://api.eu.residency.elevenlabs.io"
    assert settings.whatsapp_notification_phone_number_id is None
    assert settings.whatsapp_notification_template_name is None


def test_channel_settings_are_read_from_the_environment() -> None:
    settings = assemble_app_settings(
        {
            "ELEVENLABS_API_BASE_URL": "https://api.eu.residency.elevenlabs.io",
            "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID": " 106540352242922 ",
            "WHATSAPP_NOTIFICATION_TEMPLATE": "staff_notification",
        }
    )

    assert settings.elevenlabs_api_base_url == "https://api.eu.residency.elevenlabs.io"
    assert settings.whatsapp_notification_phone_number_id == "106540352242922"
    assert settings.whatsapp_notification_template_name == "staff_notification"


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("ELEVENLABS_API_BASE_URL", "not a url"),
        ("WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID", "+995 32 200"),
        ("WHATSAPP_NOTIFICATION_TEMPLATE", "Staff Notification"),
    ],
)
def test_malformed_channel_settings_are_refused(variable: str, value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        assemble_app_settings({variable: value})


def test_production_refuses_a_non_eu_elevenlabs_host_unless_allowed() -> None:
    production: dict[str, str] = {
        "APP_ENV": "production",
        "ENCRYPTION_KEY": "production-encryption-secret-0123456789",
        "ELEVENLABS_API_BASE_URL": "https://api.elevenlabs.io",
    }

    with pytest.raises(ValidationFailedError, match="outside the EU"):
        assemble_app_settings(production)

    allowed = assemble_app_settings(
        {**production, "ELEVENLABS_ALLOW_NON_EU_REGION": "true"}
    )
    assert allowed.elevenlabs_api_base_url == "https://api.elevenlabs.io"
    development = assemble_app_settings(
        {"ELEVENLABS_API_BASE_URL": "https://api.elevenlabs.io"}
    )
    assert development.elevenlabs_api_base_url == "https://api.elevenlabs.io"
