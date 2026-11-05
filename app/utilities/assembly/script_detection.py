"""
Is a reply written in the script of the expected language?

Checks only the writing system (ISO 15924), which code can see reliably:
a Georgian, Hebrew or Japanese customer must get an answer in that script,
and a Latin-script customer must not get an answer in Cyrillic. Languages
sharing a script (Italian and English) are left to the judge.
"""

import re
import unicodedata
from collections.abc import Iterator

from app.schemas.typings.localization.constrained_strings import ScriptCode

type CodePointRange = tuple[int, int]

# Vowel signs of Thai, Devanagari, Bengali and similar scripts are
# combining marks: they are part of the words of their script.
COMBINING_MARK_CATEGORIES: frozenset[str] = frozenset({"Mn", "Mc"})
ACRONYM_PATTERN: re.Pattern[str] = re.compile(r"[A-Z]{2,5}")
MIN_SCRIPT_SHARE_NUMERATOR: int = 1
MIN_SCRIPT_SHARE_DENOMINATOR: int = 2
CJK_IDEOGRAPHS: tuple[CodePointRange, ...] = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2FA1F),
)
HANGUL: tuple[CodePointRange, ...] = (
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xAC00, 0xD7AF),
)
SCRIPT_RANGES: dict[str, tuple[CodePointRange, ...]] = {
    "Latn": (
        (0x0041, 0x005A),
        (0x0061, 0x007A),
        (0x00C0, 0x024F),
        (0x1E00, 0x1EFF),
    ),
    "Cyrl": ((0x0400, 0x052F), (0x1C80, 0x1C8F), (0x2DE0, 0x2DFF), (0xA640, 0xA69F)),
    "Geor": ((0x10A0, 0x10FF), (0x1C90, 0x1CBF), (0x2D00, 0x2D2F)),
    "Armn": ((0x0530, 0x058F), (0xFB13, 0xFB17)),
    "Grek": ((0x0370, 0x03FF), (0x1F00, 0x1FFF)),
    "Hebr": ((0x0590, 0x05FF), (0xFB1D, 0xFB4F)),
    "Arab": (
        (0x0600, 0x06FF),
        (0x0750, 0x077F),
        (0x08A0, 0x08FF),
        (0xFB50, 0xFDFF),
        (0xFE70, 0xFEFF),
    ),
    "Thai": ((0x0E00, 0x0E7F),),
    "Laoo": ((0x0E80, 0x0EFF),),
    "Khmr": ((0x1780, 0x17FF),),
    "Mymr": ((0x1000, 0x109F),),
    "Tibt": ((0x0F00, 0x0FFF),),
    "Deva": ((0x0900, 0x097F), (0xA8E0, 0xA8FF)),
    "Beng": ((0x0980, 0x09FF),),
    "Guru": ((0x0A00, 0x0A7F),),
    "Gujr": ((0x0A80, 0x0AFF),),
    "Orya": ((0x0B00, 0x0B7F),),
    "Taml": ((0x0B80, 0x0BFF),),
    "Telu": ((0x0C00, 0x0C7F),),
    "Knda": ((0x0C80, 0x0CFF),),
    "Mlym": ((0x0D00, 0x0D7F),),
    "Sinh": ((0x0D80, 0x0DFF),),
    "Thaa": ((0x0780, 0x07BF),),
    "Ethi": ((0x1200, 0x139F), (0x2D80, 0x2DDF)),
    "Hans": CJK_IDEOGRAPHS,
    "Hant": CJK_IDEOGRAPHS,
    "Hani": CJK_IDEOGRAPHS,
    "Jpan": ((0x3040, 0x309F), (0x30A0, 0x30FF), (0x31F0, 0x31FF), *CJK_IDEOGRAPHS),
    "Kore": (*HANGUL, *CJK_IDEOGRAPHS),
    "Hang": HANGUL,
}


def is_written_in_script(text: str, script_code: ScriptCode | None) -> bool | None:
    """
    True when at least half of the letters belong to the script, False when
    fewer do, None when it cannot be told (unknown script, no letters).

    Short upper-case Latin tokens ("AI", "GEL", "VR", "SMS") are ignored, and
    a Latin business name inside a Georgian reply does not flip the result.
    """

    if script_code is None:
        return None

    ranges: tuple[CodePointRange, ...] | None = SCRIPT_RANGES.get(str(script_code))
    if ranges is None:
        return None

    letter_count: int = 0
    script_letter_count: int = 0
    for word in iter_words(text):
        if ACRONYM_PATTERN.fullmatch(word):
            continue

        for character in word:
            code_point: int = ord(character)
            is_in_script: bool = any(
                start <= code_point <= end for start, end in ranges
            )
            if not character.isalpha() and not is_in_script:
                continue  # a mark of another script tells nothing

            letter_count += 1
            if is_in_script:
                script_letter_count += 1

    if letter_count == 0:
        return None

    return (
        script_letter_count * MIN_SCRIPT_SHARE_DENOMINATOR
        >= letter_count * MIN_SCRIPT_SHARE_NUMERATOR
    )


def iter_words(text: str) -> Iterator[str]:
    """Runs of letters together with their combining marks (vowel signs)."""

    word: list[str] = []
    for character in text:
        if character.isalpha() or (
            word != [] and unicodedata.category(character) in COMBINING_MARK_CATEGORIES
        ):
            word.append(character)
            continue

        if word:
            yield "".join(word)
            word = []

    if word:
        yield "".join(word)
