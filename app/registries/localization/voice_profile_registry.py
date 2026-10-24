"""
The voice of the phone assistant in each language (ElevenLabs voices).

A language the low-latency speech model says well (Russian, English,
German, Ukrainian) gets it; Georgian, Hebrew and every other language get
the conversational v3 model, the platform's model with the widest choice
of languages, and a steadier voice: a model that speaks a language less
often drifts less when it speaks evenly. The voices are premade voices of
the ElevenLabs library, which every workspace has.

The choice is a starting point: the pilot calls in Tbilisi measure how
callers understand each voice and how often a booking comes out right,
and this table changes with what they show (docs/LAUNCH.md, 4.6).
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.contracts.voice_platform import VoiceProfileRegistryContract
from app.schemas.dto.voice import VoiceProfile
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.voice.constrained_floats import VoiceStability
from app.schemas.typings.voice.constrained_strings import (
    VoicePlatformVoiceId,
    VoiceTtsModelId,
)
from app.utilities.localization.language_tags import base_language_code

FLASH_MODEL: VoiceTtsModelId = VoiceTtsModelId("eleven_flash_v2_5")
CONVERSATIONAL_MODEL: VoiceTtsModelId = VoiceTtsModelId("eleven_v3_conversational")
# Premade voices of the ElevenLabs library.
MATILDA: VoicePlatformVoiceId = VoicePlatformVoiceId("XrExE9yKIg1WjnnlVkGX")
SARAH: VoicePlatformVoiceId = VoicePlatformVoiceId("EXAVITQu4vr4xnSDxMaL")
JESSICA: VoicePlatformVoiceId = VoicePlatformVoiceId("cgSgspJ2msm6clMCkdW9")
LAURA: VoicePlatformVoiceId = VoicePlatformVoiceId("FGY2WhTYpPnrIDTdsKH5")
STEADY: VoiceStability = VoiceStability(0.6)
BALANCED: VoiceStability = VoiceStability(0.5)

DEFAULT_VOICE_PROFILE: VoiceProfile = VoiceProfile(
    voice_id=MATILDA, tts_model=CONVERSATIONAL_MODEL, stability=STEADY
)
VOICE_PROFILES: Mapping[str, VoiceProfile] = MappingProxyType(
    {
        "ka": VoiceProfile(
            voice_id=MATILDA, tts_model=CONVERSATIONAL_MODEL, stability=STEADY
        ),
        "ru": VoiceProfile(voice_id=SARAH, tts_model=FLASH_MODEL, stability=BALANCED),
        "uk": VoiceProfile(voice_id=SARAH, tts_model=FLASH_MODEL, stability=BALANCED),
        "en": VoiceProfile(voice_id=JESSICA, tts_model=FLASH_MODEL, stability=BALANCED),
        "de": VoiceProfile(voice_id=LAURA, tts_model=FLASH_MODEL, stability=BALANCED),
        "he": VoiceProfile(
            voice_id=MATILDA, tts_model=CONVERSATIONAL_MODEL, stability=STEADY
        ),
    }
)


class VoiceProfileRegistry(VoiceProfileRegistryContract):
    """The tuned voice of each language, read from `VOICE_PROFILES`."""

    def __init__(
        self,
        profiles: Mapping[str, VoiceProfile] = VOICE_PROFILES,
        default_profile: VoiceProfile = DEFAULT_VOICE_PROFILE,
    ) -> None:
        self._profiles: Mapping[str, VoiceProfile] = profiles
        self._default_profile: VoiceProfile = default_profile

    def get(self, language: LanguageTag) -> VoiceProfile:
        exact: VoiceProfile | None = self._profiles.get(str(language).lower())
        if exact is not None:
            return exact

        return self._profiles.get(base_language_code(language), self._default_profile)
