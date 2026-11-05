"""
The recording sentence of a call's greeting in every country: said
whenever the business records calls, whatever its profile says, and always
with the way to go on without a recording (the consent where every party
must agree, the non-recorded path elsewhere).
"""

import pytest

from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.conversations import CallGreetingRequest
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from tests.brain.brain_world import build_world
from tests.brain.business_setups import BusinessSetup
from tests.brain.call_recording_settings import record_calls
from tests.brain.scripted_turns import scripted


@pytest.mark.parametrize("country", ["GE", "DE", "US", "ZZ"])
def test_recorded_calls_always_say_so_whatever_the_profile_says(
    country: str,
) -> None:
    world = build_world(
        scripted(),
        BusinessSetup(country_code=country if country != "ZZ" else "GE"),
    )
    record_calls(world)
    profile = world.profile_repo.get_by_business(world.business.id)
    assert isinstance(profile, BusinessProfileDocument)
    profile.is_recording_notice_enabled = False
    world.profile_repo.save(profile)
    if country == "ZZ":
        world.business.country_code = CountryCode("ZZ")
        world.save_business(world.business)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("en"))
    )

    assert "The call is recorded." in greeting.text


@pytest.mark.parametrize(
    ("country", "language", "expected"),
    [
        (
            "DE",
            "de",
            "Hallo! Hier spricht der KI-Assistent von Sakhli. Das Gespräch wird "
            "aufgezeichnet. Wenn Sie das nicht möchten, sagen Sie es einfach, "
            "dann sprechen wir ohne Aufzeichnung weiter. Um mit einem Mitarbeiter "
            "zu sprechen, sagen Sie „Mitarbeiter“. Sakhli ist für Ihre Daten "
            "verantwortlich und nutzt sie nur, um Ihr Anliegen zu bearbeiten. Die "
            "vollständigen Datenschutzhinweise finden Sie auf unserer Webseite, "
            "oder fragen Sie mich nach dem Link.",
        ),
        (
            "US",
            "en",
            "Hello! This is the AI assistant of Sakhli. The call is recorded. If "
            "you do not want it recorded, just say so and we will continue without "
            'a recording. To talk to a staff member, say "operator". Sakhli is '
            "responsible for your data and uses it only to handle your request. "
            "For the full privacy notice, ask me for the link or see our web page.",
        ),
    ],
)
def test_all_party_consent_countries_let_the_caller_decline_the_recording(
    country: str, language: str, expected: str
) -> None:
    world = build_world(
        scripted(), BusinessSetup(country_code=country, languages=(language,))
    )
    record_calls(world)

    greeting = world.greeting.run(
        CallGreetingRequest(
            business_id=world.business.id, language=LanguageTag(language)
        )
    )

    assert greeting.text == expected


@pytest.mark.parametrize("country", ["GE", "IL"])
def test_notice_countries_offer_the_call_without_a_recording_too(
    country: str,
) -> None:
    # Where a notice is enough (Italy too), a recording is not necessary
    # for the call: the caller may still go on without one (GDPR art. 25).
    world = build_world(scripted(), BusinessSetup(country_code=country))
    record_calls(world)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("en"))
    )

    assert (
        "The call is recorded. If you do not want it recorded, just say so and "
        "we will continue without a recording. To talk"
    ) in greeting.text


def test_a_country_the_platform_does_not_know_asks_for_consent() -> None:
    world = build_world(scripted())
    record_calls(world)
    world.business.country_code = CountryCode("ZZ")
    world.save_business(world.business)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("en"))
    )

    assert "without a recording" in greeting.text
