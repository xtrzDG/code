"""Display language of a request: `?language=` and the Accept-Language header."""

import re

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import LanguageTag

# One Accept-Language item: a language range and an optional quality weight.
ACCEPT_LANGUAGE_ITEM_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(?P<tag>[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*)"
    r"\s*(?:;\s*q\s*=\s*(?P<q>[0-9.]+))?\s*$"
)


def parse_language_parameter(raw_value: str | None) -> LanguageTag | None:
    """
    A BCP 47 tag from a query parameter, tolerant of letter case ("pt-br").

    Raises:
        ValidationFailedError: the value is not a language tag.
    """

    if raw_value is None or raw_value.strip() == "":
        return None

    language_tag: LanguageTag | None = canonical_language_tag(raw_value.strip())
    if language_tag is None:
        raise ValidationFailedError("Query parameter language is not valid.")

    return language_tag


def negotiate_language(accept_language: str | None) -> LanguageTag | None:
    """The preferred valid language of an Accept-Language header, if any."""

    if accept_language is None:
        return None

    candidates: list[tuple[float, int, LanguageTag]] = []
    for position, raw_item in enumerate(accept_language.split(",")):
        match: re.Match[str] | None = ACCEPT_LANGUAGE_ITEM_PATTERN.match(raw_item)
        if match is None:
            continue

        quality: float = parse_quality(match.group("q"))
        language_tag: LanguageTag | None = canonical_language_tag(match.group("tag"))
        if language_tag is not None and quality > 0.0:
            candidates.append((-quality, position, language_tag))

    if candidates == []:
        return None

    return min(candidates)[2]


def parse_quality(raw_quality: str | None) -> float:
    """The q weight of an Accept-Language item; malformed weights count as 0."""

    if raw_quality is None:
        return 1.0

    try:
        return float(raw_quality)
    except ValueError:
        return 0.0


def canonical_language_tag(raw_tag: str) -> LanguageTag | None:
    """
    Normalize letter case of a language tag ("EN-us" -> "en-US").

    Returns None when the tag is not a language[-Script][-REGION] tag.
    """

    parts: list[str] = raw_tag.replace("_", "-").split("-")
    canonical_parts: list[str] = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 4 and part.isalpha():
            canonical_parts.append(part.title())
        elif len(part) == 2 and part.isalpha():
            canonical_parts.append(part.upper())
        else:
            canonical_parts.append(part)

    try:
        return LanguageTag("-".join(canonical_parts))
    except ValueError:
        return None
