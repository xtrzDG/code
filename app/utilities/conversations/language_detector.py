import re
import unicodedata
from collections import Counter
from functools import cache

from app.contracts.localization_utilities import LanguageDetectorContract
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

WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+")
KANA_SCRIPT: str = "Kana"
COMBINING_MARK_CATEGORIES: frozenset[str] = frozenset({"Mn", "Mc"})
HAN_SCRIPT: str = "Hani"
FREQUENT_WORD_WEIGHT: int = 2
DISTINCTIVE_LETTER_WEIGHT: int = 3
FOREIGN_LETTER_WEIGHT: int = 2


class LanguageDetector(LanguageDetectorContract):
    """
    Pick the candidate language a customer message is written in.

    1. The dominant writing system is found from Unicode blocks (Georgian,
       Armenian, Hebrew, Arabic, Cyrillic, Greek, Thai, Lao, Khmer, Myanmar,
       Devanagari, Bengali and the other Indic scripts, Sinhala, Ethiopic,
       Thaana, Tibetan, Han, Kana, Hangul, Latin), counting the vowel signs
       of a script with its letters. Kana makes Han text Japanese.
    2. Candidates written in that script (CLDR likely script of each tag)
       remain; one candidate wins at once.
    3. Several candidates are scored by frequent words, letters only their
       language uses and letters their alphabet lacks (Ukrainian "і"
       against Russian, Turkish against Azerbaijani "ə", Polish "ł", ...).

    Matching is by base language, so Portuguese text selects a "pt-BR"
    candidate. Text without letters, a script no candidate uses, or a tie
    returns the fallback (when it is among the tied candidates).
    """

    def detect(
        self,
        text: str,
        candidate_languages: list[LanguageTag],
        fallback_language: LanguageTag,
    ) -> LanguageTag:
        lowered_text: str = text.lower()
        dominant_script: str | None = find_dominant_script(lowered_text)
        if dominant_script is None:
            return fallback_language

        compatible_scripts: frozenset[str] = COMPATIBLE_TAG_SCRIPTS.get(
            dominant_script,
            frozenset({dominant_script}),
        )
        script_candidates: list[LanguageTag] = [
            candidate
            for candidate in unique_tags(candidate_languages)
            if find_likely_script_code(candidate) in compatible_scripts
        ]
        if not script_candidates:
            return fallback_language

        if len(script_candidates) == 1:
            return script_candidates[0]

        if dominant_script == HAN_SCRIPT:
            return prefer_chinese(script_candidates)

        return choose_by_evidence(
            lowered_text,
            dominant_script,
            script_candidates,
            fallback_language,
        )


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


def unique_tags(candidate_languages: list[LanguageTag]) -> list[LanguageTag]:
    unique: list[LanguageTag] = []
    for candidate in candidate_languages:
        if candidate not in unique:
            unique.append(candidate)

    return unique


def prefer_chinese(script_candidates: list[LanguageTag]) -> LanguageTag:
    """Han text without kana is Chinese when a Chinese candidate exists."""

    for candidate in script_candidates:
        if base_language_code(candidate) == "zh":
            return candidate

    return script_candidates[0]


def choose_by_evidence(
    lowered_text: str,
    dominant_script: str,
    script_candidates: list[LanguageTag],
    fallback_language: LanguageTag,
) -> LanguageTag:
    text_words: list[str] = WORD_PATTERN.findall(lowered_text)
    script_letters: list[str] = [
        character
        for character in lowered_text
        if character.isalpha() and classify_script(character) == dominant_script
    ]
    scores: dict[LanguageTag, int] = {
        candidate: score_language(
            find_evidence(candidate, dominant_script),
            lowered_text,
            text_words,
            script_letters,
        )
        for candidate in script_candidates
    }
    best_score: int = max(scores.values())
    leaders: list[LanguageTag] = [
        candidate for candidate in script_candidates if scores[candidate] == best_score
    ]
    if len(leaders) == 1 and best_score > 0:
        return leaders[0]

    if fallback_language in leaders:
        return fallback_language

    return leaders[0]


def find_evidence(
    language_tag: LanguageTag,
    script: str,
) -> LanguageEvidence | None:
    evidence: LanguageEvidence | None = LANGUAGE_EVIDENCE.get(
        base_language_code(language_tag)
    )
    if evidence is None or evidence.script != script:
        return None

    return evidence


def score_language(
    evidence: LanguageEvidence | None,
    lowered_text: str,
    text_words: list[str],
    script_letters: list[str],
) -> int:
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
