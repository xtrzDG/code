"""Display language of a request: `?language=` and the Accept-Language header."""

import re

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import LanguageTag

# The language range of one Accept-Language item, after trimming spaces. The
# item is split on ";" and "=" first, so no pattern runs over runs of spaces.
LANGUAGE_RANGE_PATTERN: re.Pattern[str] = re.compile(
    r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*"
)
QUALITY_VALUE_PATTERN: re.Pattern[str] = re.compile(r"[0-9.]+")
# Real browsers send a few hundred characters at most; longer headers are cut.
MAX_ACCEPT_LANGUAGE_LENGTH: int = 1024
MAX_ACCEPT_LANGUAGE_ITEMS: int = 32


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
    raw_items: list[str] = accept_language[:MAX_ACCEPT_LANGUAGE_LENGTH].split(",")
    for position, raw_item in enumerate(raw_items[:MAX_ACCEPT_LANGUAGE_ITEMS]):
        item: tuple[str, str | None] | None = split_accept_language_item(raw_item)
        if item is None:
            continue

        raw_tag, raw_quality = item
        quality: float = parse_quality(raw_quality)
        language_tag: LanguageTag | None = canonical_language_tag(raw_tag)
        if language_tag is not None and quality > 0.0:
            candidates.append((-quality, position, language_tag))

    if candidates == []:
        return None

    return min(candidates)[2]


def split_accept_language_item(raw_item: str) -> tuple[str, str | None] | None:
    """
    The language range and the raw q weight of one item ("en-US;q=0.8"), or
    None when the item is not a language range with an optional q weight.
    """

    raw_range, separator, raw_parameter = raw_item.partition(";")
    language_range: str = raw_range.strip()
    if LANGUAGE_RANGE_PATTERN.fullmatch(language_range) is None:
        return None

    if separator == "":
        return language_range, None

    name, equals, raw_value = raw_parameter.partition("=")
    value: str = raw_value.strip()
    if (
        name.strip() != "q"
        or equals == ""
        or QUALITY_VALUE_PATTERN.fullmatch(value) is None
    ):
        return None

    return language_range, value


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
