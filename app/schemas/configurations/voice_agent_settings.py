from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.voice.booleans import AreVoiceChecksEnabled
from app.schemas.typings.voice.constrained_floats import VoiceAgentTemperature
from app.schemas.typings.voice.constrained_integers import VoiceTurnTimeoutSeconds
from app.schemas.typings.voice.constrained_strings import VoiceAgentLlmId

DEFAULT_VOICE_AGENT_LLM: str = "gemini-2.5-flash"
DEFAULT_VOICE_AGENT_TEMPERATURE: float = 0.2
DEFAULT_VOICE_TURN_TIMEOUT_SECONDS: int = 8


class VoiceAgentSettings(ImmutableDTO):
    """
    How every business's voice agent is tuned (R16-VOICE-TUNING), written
    into the agent whenever it is set up:

    - `llm_model` (ELEVENLABS_AGENT_LLM, `gemini-2.5-flash`): the language
      model the voice platform runs the agent on, by the platform's name;
      a fast one, as a caller hears every second of its thinking;
    - `temperature` (ELEVENLABS_AGENT_TEMPERATURE, 0.2, from 0 to 1): low,
      so dates, times and party sizes are repeated, not reworded;
    - `turn_timeout_seconds` (ELEVENLABS_TURN_TIMEOUT_SECONDS, 8, from 1 to
      30): how long the agent waits for a silent caller before it asks
      whether they are still there;
    - `are_checks_enabled` (VOICE_CHECKS_ENABLED, on): the autotests of a
      version with voice include simulated calls in its languages, which
      must pass before the version goes live; turned off, versions with
      voice are tested in chat only (while the platform's testing fails).
    """

    llm_model: VoiceAgentLlmId = VoiceAgentLlmId(DEFAULT_VOICE_AGENT_LLM)
    temperature: VoiceAgentTemperature = VoiceAgentTemperature(
        DEFAULT_VOICE_AGENT_TEMPERATURE
    )
    turn_timeout_seconds: VoiceTurnTimeoutSeconds = VoiceTurnTimeoutSeconds(
        DEFAULT_VOICE_TURN_TIMEOUT_SECONDS
    )
    are_checks_enabled: AreVoiceChecksEnabled = True
