"""Locale-aware rendering of dates and values inside localized texts.

Dates are written with CLDR patterns (Babel) in the same language as the
chosen text template, so a sentence never mixes languages. Values inserted
into right-to-left text (Hebrew, Arabic) are wrapped in Unicode directional
isolates so names, phone numbers and times keep their own direction.
"""

from datetime import date

from babel import Locale, UnknownLocaleError
from babel.dates import format_date

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag

ENGLISH: LanguageTag = LanguageTag("en")
FIRST_STRONG_ISOLATE: str = "⁨"
POP_DIRECTIONAL_ISOLATE: str = "⁩"
RIGHT_TO_LEFT: str = "right-to-left"


def choose_template_language(
    template: LocalizedText,
    requested_language: LanguageTag,
) -> LanguageTag:
    """
    Language of the template value that will be used: the requested tag,
    else its base language, else English (always present in templates).
    """

    if requested_language in template.values:
        return requested_language

    base_language = LanguageTag(str(requested_language).split("-")[0])
    if base_language in template.values:
        return base_language

    return ENGLISH


def find_locale(language: LanguageTag) -> Locale:
    """CLDR locale of a language tag, English when CLDR does not know it."""

    try:
        return Locale.parse(str(language), sep="-")
    except UnknownLocaleError, ValueError:
        return Locale.parse(str(ENGLISH))


def is_right_to_left(language: LanguageTag) -> bool:
    return find_locale(language).character_order == RIGHT_TO_LEFT


def format_full_date(value: date, language: LanguageTag) -> str:
    """Date with weekday, e.g. "Monday, October 5, 2026" / "5 Ekim 2026 Pazartesi"."""

    return format_date(value, "full", locale=find_locale(language))


def format_weekday(value: date, language: LanguageTag) -> str:
    return format_date(value, "EEEE", locale=find_locale(language))


def isolate(value: str, language: LanguageTag) -> str:
    """Wrap a value for safe embedding into text of the given language."""

    if not is_right_to_left(language):
        return value

    return f"{FIRST_STRONG_ISOLATE}{value}{POP_DIRECTIONAL_ISOLATE}"
