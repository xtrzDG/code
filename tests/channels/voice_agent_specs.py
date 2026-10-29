"""Voice agent specs and a provisioner over a recording transport."""

import json

from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.registries.localization.voice_profile_registry import VoiceProfileRegistry
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmToolDefinition
from app.schemas.dto.voice import LanguageVoiceProfile, VoiceAgentSpec, VoiceGreeting
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
    VoiceAgentId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.voice.constrained_floats import VoiceAgentTemperature
from app.schemas.typings.voice.constrained_integers import VoiceTurnTimeoutSeconds
from app.schemas.typings.voice.constrained_strings import AsrKeyword, VoiceAgentLlmId
from app.utilities.channels.webhook_signatures import derive_voice_tool_secret
from tests.channels.channels_settings import ELEVENLABS_WEBHOOK_SECRET
from tests.channels.testbed import ChannelsTestbed

BUSINESS_ID = BusinessId()
VOICES = VoiceProfileRegistry()
TOOL_SECRET: str = str(
    derive_voice_tool_secret(PlatformSecret(ELEVENLABS_WEBHOOK_SECRET), BUSINESS_ID)
)
BOOKING_SCHEMA: str = json.dumps(
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "Guest name"},
            "starts_at": {"type": "string", "format": "date-time"},
            "party_size": {"type": "integer", "minimum": 1},
        },
        "required": ["name", "starts_at", "party_size"],
    }
)


def tool(name: AssistantToolName, schema: str = BOOKING_SCHEMA) -> LlmToolDefinition:
    return LlmToolDefinition(
        name=name,
        description=LlmToolDescription(f"Use {name.value}."),
        input_schema_json=LlmToolInputSchemaJson(schema),
    )


def build_spec(
    existing_agent_id: str | None = None,
    tools: list[LlmToolDefinition] | None = None,
    languages: tuple[str, ...] = ("ka", "ru", "en"),
) -> VoiceAgentSpec:
    return VoiceAgentSpec(
        business_id=BUSINESS_ID,
        existing_agent_id=None
        if existing_agent_id is None
        else VoiceAgentId(existing_agent_id),
        business_name=BusinessName("Funicular VR"),
        languages=[LanguageTag(tag) for tag in languages],
        default_language=LanguageTag(languages[0]),
        prompt_text=SystemPromptText("You are the AI assistant of Funicular VR."),
        greetings=[
            VoiceGreeting(
                language=LanguageTag(tag), text=MessageText(f"Greeting {tag}")
            )
            for tag in languages
        ],
        tools=tools
        if tools is not None
        else [
            tool(AssistantToolName.CREATE_BOOKING),
            tool(AssistantToolName.SEARCH_KNOWLEDGE, '{"type": "object"}'),
        ],
        tool_webhook_base_url=PublicBaseUrl("https://api.workshop.test/"),
        voice_profiles=[
            LanguageVoiceProfile(
                language=LanguageTag(tag), profile=VOICES.get(LanguageTag(tag))
            )
            for tag in languages
        ],
        llm_model=VoiceAgentLlmId("gemini-2.5-flash"),
        temperature=VoiceAgentTemperature(0.2),
        asr_keywords=[AsrKeyword("Funicular VR"), AsrKeyword("VR arena 2")],
        turn_timeout_seconds=VoiceTurnTimeoutSeconds(8),
    )


def provisioner(testbed: ChannelsTestbed) -> ElevenLabsVoiceAgentProvisioner:
    return ElevenLabsVoiceAgentProvisioner(testbed.elevenlabs_client, testbed.settings)


def voice_of(tag: str) -> dict[str, object]:
    """The `tts` part the agent carries for a language of `build_spec`."""

    profile = VOICES.get(LanguageTag(tag))
    return {
        "voice_id": str(profile.voice_id),
        "model_id": str(profile.tts_model),
        "stability": float(profile.stability),
    }
