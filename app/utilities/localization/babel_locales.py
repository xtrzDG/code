"""The Babel locale used to render names, numbers and money for a language.

Tags are limited to language, optional script and optional region, the shape
`LanguageTag` allows. CLDR data comes from Babel; nothing here is hard-coded
per country or language except the CLDR placeholder codes.
"""

from functools import cache, lru_cache

from babel import Locale, localedata

from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.cldr_language_names import is_known_language_tag
from app.utilities.localization.language_scripts import (
    UNKNOWN_SCRIPT_CODE,
    find_likely_script_code,
)
from app.utilities.localization.language_tags import (
    LanguageTagParts,
    split_language_tag,
    split_language_tag_text,
)

# Tags come from requests, so lookups are cached with a bound.
MAX_CACHED_LOCALES: int = 2048


def find_babel_locale(language_tag: LanguageTag) -> Locale | None:
    """
    Most specific Babel locale with data for the tag, or None.

    "ru-GE" has no locale data of its own and falls back to "ru"; a language
    without any CLDR locale data returns None.
    """

    if not is_known_language_tag(language_tag):
        return None

    parts: LanguageTagParts = split_language_tag(language_tag)
    script_code: str = find_likely_script_code(language_tag)
    if parts.script is not None or script_code == UNKNOWN_SCRIPT_CODE:
        return find_babel_locale_by_identifier(str(language_tag))

    # "pa-PK" is written in Arabic script: prefer pa_Arab_PK over pa (Gurmukhi).
    subtags: list[str] = [parts.language, script_code]
    if parts.region is not None:
        subtags.append(parts.region)

    return find_babel_locale_by_identifier("-".join(subtags))


def require_babel_locale(language_tag: LanguageTag) -> Locale:
    """
    Babel locale used to render names, numbers and money for a language.

    Raises:
        UnsupportedLanguageError: no CLDR locale data for the language.
    """

    babel_locale: Locale | None = find_babel_locale(language_tag)
    if babel_locale is None:
        raise UnsupportedLanguageError(
            f"Texts cannot be shown in language {language_tag}."
        )

    return babel_locale


@lru_cache(maxsize=MAX_CACHED_LOCALES)
def find_babel_locale_by_identifier(language_tag_text: str) -> Locale | None:
    parts: LanguageTagParts = split_language_tag_text(language_tag_text)
    candidate_identifiers: list[str] = []
    if parts.script is not None and parts.region is not None:
        candidate_identifiers.append(f"{parts.language}_{parts.script}_{parts.region}")

    if parts.script is not None:
        candidate_identifiers.append(f"{parts.language}_{parts.script}")

    if parts.region is not None:
        candidate_identifiers.append(f"{parts.language}_{parts.region}")

    candidate_identifiers.append(parts.language)
    available_identifiers: frozenset[str] = load_locale_identifiers()
    for candidate_identifier in candidate_identifiers:
        if candidate_identifier in available_identifiers:
            return Locale.parse(candidate_identifier)

    return None


@cache
def load_locale_identifiers() -> frozenset[str]:
    """Identifiers of every locale Babel ships data for ("ka", "pt_BR", ...)."""

    return frozenset(localedata.locale_identifiers())
