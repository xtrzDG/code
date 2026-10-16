"""
Curated language defaults per country.

Countries without an entry get defaults derived from CLDR (official and de
facto official languages by number of speakers, plus English for tourists).
Entries cover the concept's expansion order (Georgia -> Armenia -> Israel ->
Kazakhstan -> Poland and the Baltics -> the USA) and countries whose CLDR
data would give an odd default (a dialect, three Norwegian standards, ...).
"""

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)


def build_language_tags(*language_tags: str) -> tuple[LanguageTag, ...]:
    return tuple(LanguageTag(language_tag) for language_tag in language_tags)


# Languages the assistant greets and answers in from the start.
CURATED_CUSTOMER_LANGUAGES: dict[CountryCode, tuple[LanguageTag, ...]] = {
    # Concept: start with Georgian, Russian and English.
    CountryCode("GE"): build_language_tags("ka", "ru", "en"),
    CountryCode("AM"): build_language_tags("hy", "ru", "en"),
    CountryCode("IL"): build_language_tags("he", "en", "ru", "ar"),
    CountryCode("KZ"): build_language_tags("ru", "kk", "en"),
    CountryCode("PL"): build_language_tags("pl", "en"),
    CountryCode("LT"): build_language_tags("lt", "en", "ru"),
    CountryCode("LV"): build_language_tags("lv", "en", "ru"),
    CountryCode("EE"): build_language_tags("et", "en", "ru"),
    CountryCode("US"): build_language_tags("en", "es"),
    CountryCode("AE"): build_language_tags("ar", "en"),
    CountryCode("AZ"): build_language_tags("az", "ru", "en"),
    CountryCode("CA"): build_language_tags("en", "fr"),
    CountryCode("CH"): build_language_tags("de", "fr", "it", "en"),
    CountryCode("LI"): build_language_tags("de", "en"),
    CountryCode("LU"): build_language_tags("fr", "de", "en"),
    CountryCode("NO"): build_language_tags("nb", "en"),
    CountryCode("TR"): build_language_tags("tr", "en"),
    CountryCode("TW"): build_language_tags("zh-Hant", "en"),
}

# Languages switched on when the owner asks (tourists and large communities).
CURATED_ON_REQUEST_LANGUAGES: dict[CountryCode, tuple[LanguageTag, ...]] = {
    # Concept: Turkish, Hebrew, Arabic and Armenian on request.
    CountryCode("GE"): build_language_tags("tr", "he", "ar", "hy"),
    CountryCode("AM"): build_language_tags("fa", "fr", "ka"),
    CountryCode("IL"): build_language_tags("fr", "uk", "es"),
    CountryCode("KZ"): build_language_tags("uz", "tr", "zh"),
    CountryCode("PL"): build_language_tags("uk", "ru", "de"),
    CountryCode("LT"): build_language_tags("pl", "de"),
    CountryCode("LV"): build_language_tags("de", "lt"),
    CountryCode("EE"): build_language_tags("fi", "de"),
    CountryCode("US"): build_language_tags("ru", "zh", "vi", "ko", "fr"),
    CountryCode("AE"): build_language_tags("hi", "ur", "ru"),
    CountryCode("AZ"): build_language_tags("tr", "fa", "ar"),
    CountryCode("TR"): build_language_tags("ru", "de", "ar"),
}

# Language of the owner's cabinet, contracts and notifications.
CURATED_OWNER_LANGUAGES: dict[CountryCode, LanguageTag] = {
    CountryCode("GE"): LanguageTag("ka"),
    CountryCode("AM"): LanguageTag("hy"),
    CountryCode("IL"): LanguageTag("he"),
    CountryCode("KZ"): LanguageTag("ru"),
    CountryCode("PL"): LanguageTag("pl"),
    CountryCode("LT"): LanguageTag("lt"),
    CountryCode("LV"): LanguageTag("lv"),
    CountryCode("EE"): LanguageTag("et"),
    CountryCode("US"): LanguageTag("en"),
    CountryCode("AE"): LanguageTag("en"),
    CountryCode("CH"): LanguageTag("de"),
    # Business and contracts run in English although CLDR counts more
    # Swahili speakers.
    CountryCode("KE"): LanguageTag("en"),
    CountryCode("UG"): LanguageTag("en"),
    CountryCode("NO"): LanguageTag("nb"),
    CountryCode("TW"): LanguageTag("zh-Hant"),
}

# English is added to every derived default so tourists can be served.
TOURIST_LANGUAGE: LanguageTag = LanguageTag("en")
MAX_DERIVED_OFFICIAL_LANGUAGES: int = 3
MAX_DERIVED_ON_REQUEST_LANGUAGES: int = 3
# Share of residents (CLDR) from which a language is offered on request.
MIN_ON_REQUEST_POPULATION_PERCENT: float = 5.0
