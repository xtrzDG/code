"""Whether CLDR knows a language tag, and display names from Babel data.

Tags are limited to language, optional script and optional region, the shape
`LanguageTag` allows. CLDR data comes from Babel; nothing here is hard-coded
per country or language except the CLDR placeholder codes.
"""

from functools import cache

from babel import Locale

from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import (
    LanguageTagParts,
    split_language_tag,
)

ENGLISH_LOCALE_IDENTIFIER: str = "en"
# CLDR codes that name no real language, script or region.
PLACEHOLDER_LANGUAGE_CODES: frozenset[str] = frozenset({"mis", "mul", "und", "zxx"})
PLACEHOLDER_SCRIPT_CODES: frozenset[str] = frozenset(
    {"Zinh", "Zmth", "Zsye", "Zsym", "Zxxx", "Zyyy", "Zzzz"}
)
PLACEHOLDER_REGION_CODES: frozenset[str] = frozenset({"ZZ"})


def is_known_language_tag(language_tag: LanguageTag) -> bool:
    """True when CLDR names the language and any script and region subtags."""

    parts: LanguageTagParts = split_language_tag(language_tag)
    english_locale: Locale = get_english_locale()
    if parts.language in PLACEHOLDER_LANGUAGE_CODES:
        return False

    if read_locale_name(english_locale.languages, parts.language) is None:
        return False

    if parts.script is not None and (
        parts.script in PLACEHOLDER_SCRIPT_CODES
        or read_locale_name(english_locale.scripts, parts.script) is None
    ):
        return False

    return not (
        parts.region is not None
        and (
            parts.region in PLACEHOLDER_REGION_CODES
            or read_locale_name(english_locale.territories, parts.region) is None
        )
    )


def require_known_language_tag(language_tag: LanguageTag) -> LanguageTagParts:
    """
    Return the subtags of a tag CLDR knows.

    Raises:
        UnsupportedLanguageError: CLDR does not know the language, script or
            region.
    """

    if not is_known_language_tag(language_tag):
        raise UnsupportedLanguageError(f"Language {language_tag} is not known.")

    return split_language_tag(language_tag)


def read_locale_name(names: object, code: str) -> str | None:
    """Read one display name from a Babel locale data mapping."""

    getter: object = getattr(names, "get", None)
    if not callable(getter):
        return None

    name: object = getter(code)
    if isinstance(name, str) and name != "":
        return name

    return None


@cache
def get_english_locale() -> Locale:
    """The CLDR English locale, the reference for code validity."""

    return Locale.parse(ENGLISH_LOCALE_IDENTIFIER)
