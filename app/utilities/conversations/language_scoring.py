"""
The signals a language leaves in a short text: its writing system, its
frequent words, the letters only it uses and the letters its alphabet lacks.
Shared by both ways of detecting a language (`language_detector`,
`any_language_detection`).
"""

import unicodedata
from collections import Counter
from functools import cache

from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
)
from app.utilities.conversations.language_evidence.language_evidence_table import (
    LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.writing_scripts import (
    COMPATIBLE_TAG_SCRIPTS,
    SCRIPT_RANGES,
)
from app.utilities.localization.language_scripts import find_likely_script_code
from app.utilities.localization.language_tags import base_language_code

KANA_SCRIPT: str = "Kana"
HAN_SCRIPT: str = "Hani"
COMBINING_MARK_CATEGORIES: frozenset[str] = frozenset({"Mn", "Mc"})
FREQUENT_WORD_WEIGHT: int = 2
DISTINCTIVE_LETTER_WEIGHT: int = 3
FOREIGN_LETTER_WEIGHT: int = 2
# Tags whose evidence is recorded under another code of the same language.
EVIDENCE_ALIASES: dict[str, str] = {"no": "nb", "tl": "fil"}


def split_words(lowered_text: str) -> list[str]:
    """
    Runs of letters with their combining marks: "नमस्ते" stays one word
    although its vowel signs are marks, not letters.
    """

    found_words: list[str] = []
    word: list[str] = []
    for character in lowered_text:
        if character.isalpha() or (
            word and unicodedata.category(character) in COMBINING_MARK_CATEGORIES
        ):
            word.append(character)
            continue

        if word:
            found_words.append("".join(word))
            word = []

    if word:
        found_words.append("".join(word))

    return found_words


def find_dominant_script(lowered_text: str) -> str | None:
    """Script with the most letters; Kana and Han together count as Kana."""

    script_counts: Counter[str] = Counter()
    for character in lowered_text:
        # Vowel signs of Indic, Thai and similar scripts are combining marks,
        # not letters, yet they are written in that script.
        if not character.isalpha() and unicodedata.category(character) not in (
            COMBINING_MARK_CATEGORIES
        ):
            continue

        script: str | None = classify_script(character)
        if script is not None:
            script_counts[script] += 1

    if script_counts[KANA_SCRIPT] > 0:
        script_counts[KANA_SCRIPT] += script_counts.pop(HAN_SCRIPT, 0)

    if not script_counts:
        return None

    return script_counts.most_common(1)[0][0]


@cache
def classify_script(character: str) -> str | None:
    code_point: int = ord(character)
    for start, end, script in SCRIPT_RANGES:
        if start <= code_point <= end:
            return script

    return None


def evidence_code(language_tag: LanguageTag) -> str:
    """The code a tag's evidence is recorded under: "pt-BR" -> "pt", "no" -> "nb"."""

    base_code: str = base_language_code(language_tag)
    return EVIDENCE_ALIASES.get(base_code, base_code)


def find_evidence(
    language_tag: LanguageTag,
    script: str,
) -> LanguageEvidence | None:
    # Evidence of a language in a script other than its usual one is
    # recorded under the tag with that script ("uz-Cyrl").
    code: str = evidence_code(language_tag)
    evidence: LanguageEvidence | None = LANGUAGE_EVIDENCE.get(
        f"{code}-{script}", LANGUAGE_EVIDENCE.get(code)
    )
    if evidence is None or evidence.script != script:
        return None

    return evidence


def collect_script_letters(lowered_text: str, script: str) -> list[str]:
    """The letters of the text written in `script`."""

    return [
        character
        for character in lowered_text
        if character.isalpha() and classify_script(character) == script
    ]


def score_language(
    evidence: LanguageEvidence | None,
    lowered_text: str,
    text_words: list[str],
    script_letters: list[str],
) -> int:
    """
    Frequent words and distinctive letters count for a language, letters
    of its script its alphabet lacks count against it; 0 without evidence.
    """

    if evidence is None:
        return 0

    frequent_word_hits: int = sum(
        1 for word in text_words if word in evidence.frequent_words
    )
    distinctive_hits: int = sum(
        1 for character in lowered_text if character in evidence.distinctive_letters
    )
    foreign_hits: int = (
        0
        if evidence.alphabet is None
        else sum(1 for letter in script_letters if letter not in evidence.alphabet)
    )
    return (
        FREQUENT_WORD_WEIGHT * frequent_word_hits
        + DISTINCTIVE_LETTER_WEIGHT * distinctive_hits
        - FOREIGN_LETTER_WEIGHT * foreign_hits
    )


def is_written_in(language: LanguageTag, script: str) -> bool:
    """Whether a tag's own script (CLDR likely script) is `script`."""

    return find_likely_script_code(language) in COMPATIBLE_TAG_SCRIPTS.get(
        script, frozenset({script})
    )
