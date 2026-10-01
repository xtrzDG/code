"""
BCP 47 language tags: boundary parsing, CLDR checks and Babel locale lookup.

Tags are limited to language, optional script and optional region, the shape
`LanguageTag` allows. CLDR data comes from Babel; nothing here is hard-coded
per country or language except the CLDR placeholder codes.
"""

import re
from functools import cache, lru_cache
from typing import NamedTuple

from babel import Locale, localedata
from babel.core import get_global

from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import LanguageTag

ENGLISH_LOCALE_IDENTIFIER: str = "en"
RAW_LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(
    r"^([A-Za-z]{2,3})(?:[-_]([A-Za-z]{4}))?(?:[-_]([A-Za-z]{2}|[0-9]{3}))?$"
)
MAX_RAW_LANGUAGE_TAG_LENGTH: int = 16
# CLDR codes that name no real language, script or region.
PLACEHOLDER_LANGUAGE_CODES: frozenset[str] = frozenset({"mis", "mul", "und", "zxx"})
PLACEHOLDER_SCRIPT_CODES: frozenset[str] = frozenset(
    {"Zinh", "Zmth", "Zsye", "Zsym", "Zxxx", "Zyyy", "Zzzz"}
)
PLACEHOLDER_REGION_CODES: frozenset[str] = frozenset({"ZZ"})
# Scripts written right to left (Unicode Script property, CLDR layout data).
RIGHT_TO_LEFT_SCRIPT_CODES: frozenset[str] = frozenset(
    {
        "Adlm",
        "Arab",
        "Aran",
        "Armi",
        "Avst",
        "Chrs",
        "Cprt",
        "Elym",
        "Hatr",
        "Hebr",
        "Hung",
        "Khar",
        "Lydi",
        "Mand",
        "Mani",
        "Mend",
        "Merc",
        "Mero",
        "Narb",
        "Nbat",
        "Nkoo",
        "Orkh",
        "Ougr",
        "Palm",
        "Phli",
        "Phlp",
        "Phnx",
        "Prti",
        "Rohg",
        "Samr",
        "Sarb",
        "Sogd",
        "Sogo",
        "Syrc",
        "Thaa",
        "Yezi",
    }
)
UNKNOWN_SCRIPT_CODE: str = "Zzzz"
# Tags come from requests, so lookups are cached with a bound.
MAX_CACHED_LOCALES: int = 2048


class LanguageTagParts(NamedTuple):
    """Subtags of a language tag as Babel expects them (technical values)."""

    language: str
    script: str | None
    region: str | None


def parse_language_tag(raw_language_tag: str) -> LanguageTag:
    """
    Normalize a tag typed at a boundary: "PT_br" -> "pt-BR", "zh-hant" -> "zh-Hant".

    Only the shape is checked here; `require_known_language_tag` checks CLDR.

    Raises:
        UnsupportedLanguageError: not a language[-Script][-REGION] tag.
    """

    trimmed_tag: str = raw_language_tag.strip()
    match: re.Match[str] | None = None
    if len(trimmed_tag) <= MAX_RAW_LANGUAGE_TAG_LENGTH:
        match = RAW_LANGUAGE_TAG_PATTERN.fullmatch(trimmed_tag)

    if match is None:
        raise UnsupportedLanguageError(
            "Language must be a BCP 47 tag such as 'en', 'pt-BR' or 'zh-Hant'."
        )

    language, script, region = match.groups()
    normalized_subtags: list[str] = [language.lower()]
    if script is not None:
        normalized_subtags.append(script.title())

    if region is not None:
        normalized_subtags.append(region.upper())

    return LanguageTag("-".join(normalized_subtags))


def split_language_tag(language_tag: LanguageTag) -> LanguageTagParts:
    """Split a validated tag into language, script and region subtags."""

    return split_language_tag_text(str(language_tag))


def split_language_tag_text(language_tag_text: str) -> LanguageTagParts:
    """Split "language[-Script][-REGION]" text whose shape is already valid."""

    subtags: list[str] = language_tag_text.split("-")
    script: str | None = None
    region: str | None = None
    for subtag in subtags[1:]:
        if len(subtag) == 4:
            script = subtag
        else:
            region = subtag

    return LanguageTagParts(language=subtags[0], script=script, region=region)


def base_language_code(language_tag: LanguageTag) -> str:
    """Language subtag of a tag: "pt-BR" -> "pt" (a lookup key, not a tag)."""

    return split_language_tag(language_tag).language


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


def find_likely_script_code(language_tag: LanguageTag) -> str:
    """
    ISO 15924 script of a tag: explicit script, else CLDR likely subtags.

    "pa-PK" -> "Arab", "pa" -> "Guru", "ka" -> "Geor"; "Zzzz" when unknown.
    """

    parts: LanguageTagParts = split_language_tag(language_tag)
    if parts.script is not None:
        return parts.script

    lookup_keys: list[str] = []
    if parts.region is not None:
        lookup_keys.append(f"{parts.language}_{parts.region}")

    lookup_keys.append(parts.language)
    likely_subtags: dict[str, str] = load_likely_subtags()
    for lookup_key in lookup_keys:
        likely_identifier: str | None = likely_subtags.get(lookup_key)
        if likely_identifier is None:
            continue

        for subtag in likely_identifier.split("_")[1:]:
            if len(subtag) == 4:
                return subtag

    return UNKNOWN_SCRIPT_CODE


def is_right_to_left_script(script_code: str) -> bool:
    """True for scripts written right to left (Arabic, Hebrew, Thaana, ...)."""

    return script_code in RIGHT_TO_LEFT_SCRIPT_CODES


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


@cache
def load_likely_subtags() -> dict[str, str]:
    likely_subtags: dict[str, str] = {}
    for key, value in get_global("likely_subtags").items():
        if isinstance(value, str):
            likely_subtags[key] = value

    return likely_subtags
