"""Language codes of channel platforms derived from BCP 47 tags.

ElevenLabs Agents name languages by lower-case ISO 639-1 codes with
"pt-br" as the one regional code; WhatsApp templates use "en", "pt_BR".
"""

from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import (
    LanguageTagParts,
    parse_language_tag,
    split_language_tag,
)

# Regional variants the voice platform names separately.
VOICE_PLATFORM_REGIONAL_LANGUAGES: frozenset[str] = frozenset({"pt-br"})


def to_voice_platform_language(language_tag: LanguageTag) -> str:
    """Voice platform code of a tag: "pt-BR" -> "pt-br", "zh-Hant-TW" -> "zh"."""

    parts: LanguageTagParts = split_language_tag(language_tag)
    if parts.region is not None:
        regional_code: str = f"{parts.language}-{parts.region.lower()}"
        if regional_code in VOICE_PLATFORM_REGIONAL_LANGUAGES:
            return regional_code

    return parts.language


def from_voice_platform_language(language_code: str) -> LanguageTag | None:
    """The tag of a voice platform code ("pt-br" -> "pt-BR"); None if invalid."""

    try:
        return parse_language_tag(language_code)
    except UnsupportedLanguageError:
        return None


def to_whatsapp_template_language(
    language_tag: LanguageTag,
) -> WhatsAppTemplateLanguageCode:
    """Template language of a tag: "pt-BR" -> "pt_BR", "ka" -> "ka"."""

    parts: LanguageTagParts = split_language_tag(language_tag)
    if parts.region is not None and parts.region.isalpha():
        return WhatsAppTemplateLanguageCode(f"{parts.language}_{parts.region}")

    return WhatsAppTemplateLanguageCode(parts.language)
