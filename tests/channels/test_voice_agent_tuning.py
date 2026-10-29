"""
The tuning of a voice agent reaches ElevenLabs: the model and temperature,
a voice per language, the speech recognition's keywords, the turn timeout
and the evaluation of every call.
"""

from typing import Any

import pytest

from app.registries.localization.voice_profile_registry import (
    CONVERSATIONAL_MODEL,
    DEFAULT_VOICE_PROFILE,
    FLASH_MODEL,
    VoiceProfileRegistry,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.config_helpers.app_settings.voice_agent_settings_section import (
    read_voice_agent_settings,
)
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_agent_specs import build_spec, provisioner, voice_of


def created_agent() -> dict[str, Any]:
    testbed = ChannelsTestbed()
    testbed.elevenlabs_transport.respond(
        "POST", r"^/v1/convai/tools$", {"id": "tool_new"}
    )
    testbed.elevenlabs_transport.respond(
        "POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_1"}
    )
    provisioner(testbed).upsert_agent(build_spec())
    [request] = testbed.elevenlabs_transport.requests_to("/agents/create")
    agent: dict[str, Any] = request.json()
    return agent


def test_model_temperature_keywords_and_turn_timeout_are_written() -> None:
    config = created_agent()["conversation_config"]

    prompt = config["agent"]["prompt"]
    assert prompt["llm"] == "gemini-2.5-flash"
    assert prompt["temperature"] == 0.2
    assert config["asr"] == {
        "quality": "high",
        "keywords": ["Funicular VR", "VR arena 2"],
    }
    assert config["turn"]["turn_timeout"] == 8
    assert config["tts"] == voice_of("ka")
    assert config["language_presets"]["ru"]["overrides"]["tts"] == voice_of("ru")


def test_every_call_is_evaluated_for_its_booking_and_disclosure() -> None:
    platform = created_agent()["platform_settings"]

    criteria = platform["evaluation"]["criteria"]
    assert [criterion["id"] for criterion in criteria] == [
        "booking_correct",
        "disclosure_said",
    ]
    assert all(criterion["type"] == "prompt" for criterion in criteria)
    assert all(criterion["conversation_goal_prompt"] for criterion in criteria)
    collected = platform["data_collection"]
    assert {name: field["type"] for name, field in collected.items()} == {
        "booking_date": "string",
        "booking_time": "string",
        "party_size": "integer",
        "callback_requested": "boolean",
    }


def test_a_language_without_its_own_voice_falls_back() -> None:
    registry = VoiceProfileRegistry()

    assert registry.get(LanguageTag("ka")).tts_model == CONVERSATIONAL_MODEL
    assert registry.get(LanguageTag("ru")).tts_model == FLASH_MODEL
    assert registry.get(LanguageTag("it")).tts_model == FLASH_MODEL
    # A regional tag takes its base language's voice.
    assert registry.get(LanguageTag("en-GB")) == registry.get(LanguageTag("en"))
    assert registry.get(LanguageTag("it-CH")) == registry.get(LanguageTag("it"))
    assert registry.get(LanguageTag("it-CH")).tts_model == FLASH_MODEL
    assert registry.get(LanguageTag("hy")) == DEFAULT_VOICE_PROFILE


def test_the_tuning_variables_are_read_and_checked() -> None:
    defaults = read_voice_agent_settings({})["voice_agents"]
    assert str(defaults.llm_model) == "gemini-2.5-flash"
    assert defaults.are_checks_enabled is True

    tuned = read_voice_agent_settings(
        {
            "ELEVENLABS_AGENT_LLM": " GPT-4.1-mini ",
            "ELEVENLABS_AGENT_TEMPERATURE": "0.5",
            "ELEVENLABS_TURN_TIMEOUT_SECONDS": "12",
            "VOICE_CHECKS_ENABLED": "false",
        }
    )["voice_agents"]
    assert str(tuned.llm_model) == "gpt-4.1-mini"
    assert float(tuned.temperature) == 0.5
    assert int(tuned.turn_timeout_seconds) == 12
    assert tuned.are_checks_enabled is False


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ELEVENLABS_AGENT_TEMPERATURE", "1.5"),
        ("ELEVENLABS_TURN_TIMEOUT_SECONDS", "0"),
        ("ELEVENLABS_AGENT_LLM", "gpt 4"),
        ("VOICE_CHECKS_ENABLED", "maybe"),
    ],
)
def test_a_wrong_tuning_value_names_its_variable(name: str, value: str) -> None:
    with pytest.raises(ValidationFailedError, match=name):
        read_voice_agent_settings({name: value})
