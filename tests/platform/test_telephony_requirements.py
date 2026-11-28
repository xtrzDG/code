"""
Production refuses PHONE_NUMBER_PROVIDER=twilio without the Twilio account
or the voice platform's key (owners would silently be told to ask the team
for a number), and never refuses a Twilio account without an SMS sender.
"""

import pytest

from app.gateways.startup_checks import check_production_requirements
from app.schemas.exceptions.application_errors import ValidationFailedError
from tests.platform.production_settings import (
    container_with,
    problems_with,
    production_with,
)

TWILIO_ACCOUNT: dict[str, str | None] = {
    "TWILIO_ACCOUNT_SID": "AC" + "3d" * 16,
    "TWILIO_AUTH_TOKEN": "fake-twilio-auth-token",
}
VOICE_PLATFORM: dict[str, str | None] = {
    "ELEVENLABS_API_KEY": "fake-elevenlabs-key",
    "ELEVENLABS_WEBHOOK_SECRET": "fake-elevenlabs-webhook-secret",
}
RENTED_NUMBERS: dict[str, str | None] = {
    "PHONE_NUMBER_PROVIDER": "twilio",
    **TWILIO_ACCOUNT,
    **VOICE_PLATFORM,
}


@pytest.mark.parametrize(
    ("removed", "named"),
    [
        (
            ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "ELEVENLABS_API_KEY"),
            "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and ELEVENLABS_API_KEY, which "
            "are not set",
        ),
        (
            ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"),
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN, which are not set",
        ),
        (("ELEVENLABS_API_KEY",), "ELEVENLABS_API_KEY, which is not set"),
    ],
)
def test_twilio_numbers_without_their_keys_are_refused(
    removed: tuple[str, ...], named: str
) -> None:
    changes: dict[str, str | None] = {
        **RENTED_NUMBERS,
        **dict.fromkeys(removed),
    }

    [problem] = problems_with(changes)

    assert problem.startswith(f"PHONE_NUMBER_PROVIDER=twilio needs {named}: ")
    assert "ask the team" in problem
    assert "fake-" not in problem


def test_twilio_numbers_with_the_account_alone_start_without_an_sms_sender() -> None:
    environment = production_with(RENTED_NUMBERS)

    assert "TWILIO_FROM_NUMBER" not in environment
    assert problems_with(RENTED_NUMBERS) == []
    assert check_production_requirements(container_with(environment)) == []


@pytest.mark.parametrize(
    "changes",
    [
        TWILIO_ACCOUNT,
        {"PHONE_NUMBER_PROVIDER": None, "ELEVENLABS_API_KEY": None},
    ],
)
def test_without_rented_numbers_nothing_about_twilio_is_asked(
    changes: dict[str, str | None],
) -> None:
    assert problems_with(changes) == []


def test_the_start_is_refused_with_the_missing_keys_named() -> None:
    container = container_with(production_with({"PHONE_NUMBER_PROVIDER": "twilio"}))

    with pytest.raises(ValidationFailedError) as refused:
        check_production_requirements(container)

    message: str = str(refused.value)
    assert message.startswith("Production refuses to start (APP_ENV=production):")
    assert (
        "\n- PHONE_NUMBER_PROVIDER=twilio needs TWILIO_ACCOUNT_SID, "
        "TWILIO_AUTH_TOKEN and ELEVENLABS_API_KEY" in message
    )
