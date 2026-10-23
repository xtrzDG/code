"""
ELEVENLABS_AGENT_LLM, ELEVENLABS_AGENT_TEMPERATURE,
ELEVENLABS_TURN_TIMEOUT_SECONDS and VOICE_CHECKS_ENABLED: how the voice
agents are tuned and whether versions with voice are tested by simulated
calls.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.voice_agent_settings import (
    DEFAULT_VOICE_AGENT_LLM,
    DEFAULT_VOICE_AGENT_TEMPERATURE,
    DEFAULT_VOICE_TURN_TIMEOUT_SECONDS,
    VoiceAgentSettings,
)
from app.schemas.typings.voice.constrained_floats import VoiceAgentTemperature
from app.schemas.typings.voice.constrained_integers import VoiceTurnTimeoutSeconds
from app.schemas.typings.voice.constrained_strings import VoiceAgentLlmId
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_boolean,
    read_float,
    read_integer,
    read_text,
)


class VoiceAgentSettingsSection(TypedDict):
    """The `AppSettings` field of the voice agents' tuning."""

    voice_agents: VoiceAgentSettings


def read_voice_agent_settings(
    environment_variables: Mapping[str, str],
) -> VoiceAgentSettingsSection:
    """Every variable is optional (see `VoiceAgentSettings`)."""

    return VoiceAgentSettingsSection(
        voice_agents=VoiceAgentSettings(
            llm_model=parse_setting(
                "ELEVENLABS_AGENT_LLM",
                read_text(
                    environment_variables,
                    "ELEVENLABS_AGENT_LLM",
                    DEFAULT_VOICE_AGENT_LLM,
                ).lower(),
                VoiceAgentLlmId,
            ),
            temperature=parse_setting(
                "ELEVENLABS_AGENT_TEMPERATURE",
                read_float(
                    environment_variables,
                    "ELEVENLABS_AGENT_TEMPERATURE",
                    DEFAULT_VOICE_AGENT_TEMPERATURE,
                ),
                VoiceAgentTemperature,
            ),
            turn_timeout_seconds=parse_setting(
                "ELEVENLABS_TURN_TIMEOUT_SECONDS",
                read_integer(
                    environment_variables,
                    "ELEVENLABS_TURN_TIMEOUT_SECONDS",
                    DEFAULT_VOICE_TURN_TIMEOUT_SECONDS,
                ),
                VoiceTurnTimeoutSeconds,
            ),
            are_checks_enabled=read_boolean(
                environment_variables, "VOICE_CHECKS_ENABLED", True
            ),
        )
    )
