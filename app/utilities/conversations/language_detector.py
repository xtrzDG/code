from app.contracts.localization_utilities import LanguageDetectorContract
from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.any_language_detection import (
    LanguageContext,
    detect_any_language,
)
from app.utilities.conversations.language_evidence.writing_scripts import (
    COMPATIBLE_TAG_SCRIPTS,
)
from app.utilities.conversations.language_scoring import (
    HAN_SCRIPT,
    collect_script_letters,
    find_dominant_script,
    find_evidence,
    score_language,
    split_words,
)
from app.utilities.localization.language_scripts import find_likely_script_code
from app.utilities.localization.language_tags import base_language_code


class LanguageDetector(LanguageDetectorContract):
    """
    Tell the language a customer message is written in.

    `detect` picks one of the given candidates (the widget's starter
    questions, written by the owner in a business language):

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

    `detect_any` reads any language a customer may write, with the
    conversation's language kept when the text tells too little
    (`any_language_detection`).
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

    def detect_any(
        self,
        text: MessageText,
        version_languages: list[LanguageTag],
        default_language: LanguageTag,
        conversation_language: LanguageTag | None,
        contact_language: LanguageTag | None,
    ) -> DetectedLanguage:
        return detect_any_language(
            str(text),
            LanguageContext(
                version_languages=tuple(unique_tags(version_languages)),
                default_language=default_language,
                kept_language=conversation_language or contact_language,
            ),
        )


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
    text_words: list[str] = split_words(lowered_text)
    script_letters: list[str] = collect_script_letters(lowered_text, dominant_script)
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
