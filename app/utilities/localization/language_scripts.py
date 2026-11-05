"""The writing script of a language tag, and its direction.

Tags are limited to language, optional script and optional region, the shape
`LanguageTag` allows. CLDR data comes from Babel; nothing here is hard-coded
per country or language except the CLDR placeholder codes.
"""

from functools import cache

from babel.core import get_global

from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import (
    LanguageTagParts,
    split_language_tag,
)

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


@cache
def load_likely_subtags() -> dict[str, str]:
    likely_subtags: dict[str, str] = {}
    for key, value in get_global("likely_subtags").items():
        if isinstance(value, str):
            likely_subtags[key] = value

    return likely_subtags
