"""
Curated, honest support levels per language (by language subtag).

Voice levels follow the concept: verified where the voice platform is proven
on real calls, beta where vendors claim quality nobody measured for us, and
"needs pilot check" for everything else, Georgian first of all, until pilot
calls are measured. Text support is "supported" for languages the language
model handles well in chat (the concept: Georgian chat carries no such risk)
and "beta" for the rest.
"""

from app.schemas.constants.localization import LanguageVoiceSupport
from app.schemas.typings.localization.constrained_strings import LanguageTag

VOICE_SUPPORT_BY_LANGUAGE: dict[LanguageTag, LanguageVoiceSupport] = {
    LanguageTag("de"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("en"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("es"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("fr"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("it"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("pt"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("ru"): LanguageVoiceSupport.VERIFIED,
    LanguageTag("ar"): LanguageVoiceSupport.BETA,
    LanguageTag("he"): LanguageVoiceSupport.BETA,
    LanguageTag("hi"): LanguageVoiceSupport.BETA,
    LanguageTag("ja"): LanguageVoiceSupport.BETA,
    LanguageTag("ko"): LanguageVoiceSupport.BETA,
    LanguageTag("nl"): LanguageVoiceSupport.BETA,
    LanguageTag("pl"): LanguageVoiceSupport.BETA,
    LanguageTag("tr"): LanguageVoiceSupport.BETA,
    LanguageTag("uk"): LanguageVoiceSupport.BETA,
    LanguageTag("zh"): LanguageVoiceSupport.BETA,
    LanguageTag("az"): LanguageVoiceSupport.NEEDS_PILOT_CHECK,
    LanguageTag("hy"): LanguageVoiceSupport.NEEDS_PILOT_CHECK,
    LanguageTag("ka"): LanguageVoiceSupport.NEEDS_PILOT_CHECK,
    LanguageTag("kk"): LanguageVoiceSupport.NEEDS_PILOT_CHECK,
}
DEFAULT_VOICE_SUPPORT: LanguageVoiceSupport = LanguageVoiceSupport.NEEDS_PILOT_CHECK

TEXT_SUPPORTED_LANGUAGES: frozenset[LanguageTag] = frozenset(
    LanguageTag(language_code)
    for language_code in (
        "ar",
        "az",
        "be",
        "bg",
        "bn",
        "bs",
        "ca",
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "fa",
        "fi",
        "fil",
        "fr",
        "he",
        "hi",
        "hr",
        "hu",
        "hy",
        "id",
        "it",
        "ja",
        "ka",
        "kk",
        "ko",
        "lt",
        "lv",
        "mk",
        "ms",
        "nb",
        "nl",
        "no",
        "pl",
        "pt",
        "ro",
        "ru",
        "sk",
        "sl",
        "sq",
        "sr",
        "sv",
        "sw",
        "th",
        "tr",
        "uk",
        "ur",
        "uz",
        "vi",
        "zh",
    )
)

# Constructed, liturgical or historical languages CLDR ships data for; they
# stay valid tags but are left out of the language picker.
UNLISTED_LANGUAGES: frozenset[LanguageTag] = frozenset(
    LanguageTag(language_code)
    for language_code in (
        "cop",
        "cu",
        "eo",
        "gez",
        "ia",
        "ie",
        "io",
        "jbo",
        "la",
        "prg",
        "sa",
        "tok",
        "vo",
    )
)
# Script variants listed next to the bare languages because both are common.
EXTRA_LISTED_LANGUAGES: tuple[LanguageTag, ...] = (
    LanguageTag("sr-Latn"),
    LanguageTag("zh-Hant"),
)
