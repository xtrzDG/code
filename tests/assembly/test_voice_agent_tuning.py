"""
The tuning a published voice agent gets: a voice in each language of the
version, the business's own words for the speech recognition, and the
platform's model, temperature and turn timeout.
"""

from app.registries.localization.voice_profile_registry import VoiceProfileRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.publish_helpers import ready_version
from tests.assembly.testbed import AssemblyTestbed


def test_a_published_agent_speaks_each_language_in_its_tuned_voice() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)

    testbed.publish(business.id, version.id)

    [spec] = testbed.voice_provisioner.specs
    voices = VoiceProfileRegistry()
    assert [(str(item.language), item.profile) for item in spec.voice_profiles] == [
        (tag, voices.get(LanguageTag(tag))) for tag in ("ka", "ru", "en")
    ]
    assert str(spec.llm_model) == "gemini-2.5-flash"
    assert float(spec.temperature) == 0.2
    assert int(spec.turn_timeout_seconds) == 8


def test_the_speech_recognition_listens_for_the_business_and_its_menu() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)

    testbed.publish(business.id, version.id)

    [spec] = testbed.voice_provisioner.specs
    keywords = [str(keyword) for keyword in spec.asr_keywords]
    assert keywords[:3] == ["Café Rustaveli", "Terrace", "Table 4"]
    assert {"Khachapuri Adjaruli", "Mtsvadi"} <= set(keywords)
    # Questions, retired items and inactive resources are not listened for.
    assert not {"Is there parking?", "Old dish", "Broken table"} & set(keywords)


def test_the_tuning_variables_reach_the_agent() -> None:
    testbed = AssemblyTestbed(
        {
            "ELEVENLABS_AGENT_LLM": "claude-haiku-4-5",
            "ELEVENLABS_AGENT_TEMPERATURE": "0.4",
            "ELEVENLABS_TURN_TIMEOUT_SECONDS": "11",
        }
    )
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = ready_version(testbed, business)

    testbed.publish(business.id, version.id)

    [spec] = testbed.voice_provisioner.specs
    assert str(spec.llm_model) == "claude-haiku-4-5"
    assert float(spec.temperature) == 0.4
    assert int(spec.turn_timeout_seconds) == 11
