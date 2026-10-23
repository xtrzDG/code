from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.dto.conversations import LlmToolDefinition
from app.schemas.typings.assistants.strings import SystemPromptText, VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.voice.constrained_floats import (
    VoiceAgentTemperature,
    VoiceStability,
)
from app.schemas.typings.voice.constrained_integers import VoiceTurnTimeoutSeconds
from app.schemas.typings.voice.constrained_strings import (
    AsrKeyword,
    VoiceAgentLlmId,
    VoicePlatformVoiceId,
    VoiceTtsModelId,
)


class VoiceGreeting(ImmutableDTO):
    """First phrase of a call in one language."""

    language: LanguageTag
    text: MessageText


class VoiceProfile(ImmutableDTO):
    """
    How the agent sounds in one language: the voice of the platform's
    library, the speech model that can say the language, and how steady
    the voice speaks (`VoiceProfileRegistry`).
    """

    voice_id: VoicePlatformVoiceId
    tts_model: VoiceTtsModelId
    stability: VoiceStability


class LanguageVoiceProfile(ImmutableDTO):
    """The voice profile the agent uses for one language of the business."""

    language: LanguageTag
    profile: VoiceProfile


class VoiceAgentSpec(ImmutableDTO):
    """
    Everything the voice platform needs to create or update the agent of one
    business (concept section 4: same instruction and tools as the chat).
    """

    business_id: BusinessId
    existing_agent_id: VoiceAgentId | None = None
    business_name: BusinessName
    languages: list[LanguageTag]
    default_language: LanguageTag
    prompt_text: SystemPromptText
    greetings: list[VoiceGreeting]
    tools: list[LlmToolDefinition] = Field(default_factory=list[LlmToolDefinition])
    tool_webhook_base_url: PublicBaseUrl
    # Staff mobile a caller may be put through to during opening hours.
    transfer_phone_number: E164PhoneNumber | None = None
    # The voice of every language of the agent (the default language's is
    # the agent's own, the others its language presets').
    voice_profiles: list[LanguageVoiceProfile]
    # The language model the platform runs the agent on, and how freely it
    # words its answers (ELEVENLABS_AGENT_LLM, ELEVENLABS_AGENT_TEMPERATURE).
    llm_model: VoiceAgentLlmId
    temperature: VoiceAgentTemperature
    # What speech recognition listens for: the business's name, its
    # resources and the titles of its top items (`collect_asr_keywords`).
    asr_keywords: list[AsrKeyword] = Field(default_factory=list[AsrKeyword])
    # How long the agent waits for a silent caller before it speaks again.
    turn_timeout_seconds: VoiceTurnTimeoutSeconds
