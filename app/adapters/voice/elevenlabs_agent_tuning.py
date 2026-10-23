"""
How an ElevenLabs agent sounds and listens (R16-VOICE-TUNING): the voice
of each language, the speech recognition's keywords, the turn timeout and
the language presets that switch the greeting and the voice with the
caller's language.
"""

from app.contracts.channel_clients import JsonObject
from app.schemas.dto.spend_guard import VoiceCallLimits
from app.schemas.dto.voice import VoiceAgentSpec, VoiceGreeting, VoiceProfile
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.language_codes import to_voice_platform_language

# The platform's one setting of recognition quality ("high").
ASR_QUALITY: str = "high"


def tts_config(profile: VoiceProfile) -> JsonObject:
    """The voice, its speech model and its stability."""

    return {
        "voice_id": str(profile.voice_id),
        "model_id": str(profile.tts_model),
        "stability": float(profile.stability),
    }


def find_profile(spec: VoiceAgentSpec, language: LanguageTag) -> VoiceProfile | None:
    for language_profile in spec.voice_profiles:
        if language_profile.language == language:
            return language_profile.profile

    return None


def asr_config(spec: VoiceAgentSpec) -> JsonObject:
    """High-quality recognition that listens for the business's own words."""

    config: JsonObject = {"quality": ASR_QUALITY}
    if spec.asr_keywords:
        config["keywords"] = [str(keyword) for keyword in spec.asr_keywords]

    return config


def turn_config(spec: VoiceAgentSpec, limits: VoiceCallLimits) -> JsonObject:
    """When the agent speaks to a silent caller again, and when it hangs up."""

    return {
        "turn_timeout": int(spec.turn_timeout_seconds),
        "silence_end_call_timeout": int(limits.silence_end_seconds),
    }


def build_language_presets(spec: VoiceAgentSpec) -> JsonObject:
    """
    One preset for every language besides the default one (by the
    platform's code): its greeting as the first message and its voice.
    A language with neither gets no preset.
    """

    default_code: str = to_voice_platform_language(spec.default_language)
    presets: JsonObject = {}
    greeting_languages: list[LanguageTag] = [item.language for item in spec.greetings]
    for language in [*spec.languages, *greeting_languages]:
        code: str = to_voice_platform_language(language)
        if code == default_code or code in presets:
            continue

        overrides: JsonObject = {}
        greeting: VoiceGreeting | None = find_language_greeting(spec, code)
        if greeting is not None:
            overrides["agent"] = {"first_message": str(greeting.text), "language": code}

        profile: VoiceProfile | None = find_profile(spec, language)
        if profile is not None:
            overrides["tts"] = tts_config(profile)

        if overrides:
            presets[code] = {"overrides": overrides}

    return presets


def find_language_greeting(spec: VoiceAgentSpec, code: str) -> VoiceGreeting | None:
    """The first greeting whose language has the platform's code `code`."""

    for greeting in spec.greetings:
        if to_voice_platform_language(greeting.language) == code:
            return greeting

    return None
