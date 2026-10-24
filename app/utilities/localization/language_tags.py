"""BCP 47 language tags: boundary parsing and their subtags.

Tags are limited to language, optional script and optional region, the shape
`LanguageTag` allows. CLDR data comes from Babel; nothing here is hard-coded
per country or language except the CLDR placeholder codes.
"""

import re
from typing import NamedTuple

from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import LanguageTag

RAW_LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(
    r"^([A-Za-z]{2,3})(?:[-_]([A-Za-z]{4}))?(?:[-_]([A-Za-z]{2}|[0-9]{3}))?$"
)

MAX_RAW_LANGUAGE_TAG_LENGTH: int = 16


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
