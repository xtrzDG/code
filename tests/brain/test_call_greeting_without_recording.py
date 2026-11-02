"""
The call greeting while the business does not record calls (the default):
nothing about a recording, and the privacy notice sentence once.
"""

import pytest

from app.registries.localization.language_support_data import TEXT_SUPPORTED_LANGUAGES
from app.schemas.dto.conversations import CallGreetingRequest
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_privacy_texts import CALL_PRIVACY_NOTICE_HINT
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.business_setups import BusinessSetup
from tests.brain.call_recording_settings import record_calls
from tests.brain.scripted_turns import scripted


def greeting_of(world: BrainWorld, language: str) -> str:
    return str(
        world.greeting.run(
            CallGreetingRequest(
                business_id=world.business.id, language=LanguageTag(language)
            )
        ).text
    )


def test_a_business_without_call_settings_says_nothing_about_a_recording() -> None:
    world = build_world(scripted(), BusinessSetup(languages=("en",)))

    assert greeting_of(world, "en") == (
        "Hello! This is the AI assistant of Sakhli. To talk to a staff member, "
        'say "operator". Our privacy notice is on our web page.'
    )


@pytest.mark.parametrize("country", ["DE", "US", "GE"])
def test_recording_switched_off_asks_no_consent_anywhere(country: str) -> None:
    world = build_world(scripted(), BusinessSetup(country_code=country))
    record_calls(world, is_recording_enabled=False)

    greeting = greeting_of(world, "en")

    assert "recorded" not in greeting
    assert "without a recording" not in greeting
    assert greeting.endswith("Our privacy notice is on our web page.")


@pytest.mark.parametrize("is_recording_enabled", [True, False])
def test_the_privacy_notice_is_said_once(is_recording_enabled: bool) -> None:
    world = build_world(scripted(), BusinessSetup(languages=("it",)))
    record_calls(world, is_recording_enabled=is_recording_enabled)

    greeting = greeting_of(world, "it")

    hint = "L'informativa sulla privacy è sulla nostra pagina web."
    assert greeting.count(hint) == 1
    assert greeting.endswith(hint)
    assert ("registrata" in greeting) is is_recording_enabled


def test_the_privacy_notice_exists_in_every_supported_text_language() -> None:
    missing = sorted(
        str(tag)
        for tag in TEXT_SUPPORTED_LANGUAGES
        if tag not in CALL_PRIVACY_NOTICE_HINT.values
    )

    assert missing == []
