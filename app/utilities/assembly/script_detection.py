"""
Is a reply written in the script of the expected language?

Checks only the writing system (ISO 15924), which code can see reliably:
a Georgian, Hebrew or Japanese customer must get an answer in that script,
and a Latin-script customer must not get an answer in Cyrillic. Languages
sharing a script (Italian and English) are left to the judge.
"""

import re

from app.schemas.typings.localization.constrained_strings import ScriptCode

type CodePointRange = tuple[int, int]

# Runs of letters: Unicode word characters without digits and underscores.
WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+")
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
    "Deva": ((0x0900, 0x097F),),
    "Beng": ((0x0980, 0x09FF),),
    "Ethi": ((0x1200, 0x139F),),
    "Hans": CJK_IDEOGRAPHS,
    "Hant": CJK_IDEOGRAPHS,
    "Hani": CJK_IDEOGRAPHS,
    "Jpan": ((0x3040, 0x309F), (0x30A0, 0x30FF), (0x31F0, 0x31FF), *CJK_IDEOGRAPHS),
    "Kore": (*HANGUL, *CJK_IDEOGRAPHS),
    "Hang": HANGUL,
}


def is_detectable_script(script_code: ScriptCode | None) -> bool:
    """True when the script's letters can be recognised by code point."""

    return script_code is not None and str(script_code) in SCRIPT_RANGES


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
    for word in WORD_PATTERN.findall(text):
        if ACRONYM_PATTERN.fullmatch(word):
            continue

        for character in word:
            letter_count += 1
            code_point: int = ord(character)
            if any(start <= code_point <= end for start, end in ranges):
                script_letter_count += 1

    if letter_count == 0:
        return None

    return (
        script_letter_count * MIN_SCRIPT_SHARE_DENOMINATOR
        >= letter_count * MIN_SCRIPT_SHARE_NUMERATOR
    )
