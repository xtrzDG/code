"""
The pre-filter of the claim check: sentences of a reply that state a
policy or an availability ("Parking is free for guests.", "Мы принимаем
собак.", "უფასო Wi-Fi გვაქვს."). Questions are not claims. Only these
sentences go to the verifier model, and only when there are any.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

from app.schemas.constants.reply_safety import ClaimTopic
from app.schemas.dto.reply_safety import ClaimCandidate
from app.schemas.typings.conversations.strings import ClaimText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import base_language_code
from app.utilities.reply_guard.claim_markers import CLAIM_MARKERS
from app.utilities.reply_guard.number_word_lexicon import fold_word

SENTENCE_PATTERN: re.Pattern[str] = re.compile(r"[^.!?؟\n;]+[.!?؟]*")
WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")
QUESTION_MARKS: str = "?؟"
STEM_MARK: str = "*"
MAX_CLAIMS: int = 5
MAX_CLAIM_LENGTH: int = 300
MIN_CLAIM_LENGTH: int = 4
ENGLISH_LANGUAGE_CODE: str = "en"


@dataclass(frozen=True)
class ClaimMarkerSet:
    """The markers of one topic in the conversation's languages."""

    topic: ClaimTopic
    words: frozenset[str]
    stems: tuple[str, ...]
    phrases: tuple[str, ...]


def find_claim_candidates(
    text: str, language_tags: Iterable[LanguageTag]
) -> list[ClaimCandidate]:
    """
    The first sentences of the text that state a policy or availability in
    one of the languages (or English), at most five, as written.
    """

    marker_sets: list[ClaimMarkerSet] = load_marker_sets(
        tuple(sorted({base_language_code(tag) for tag in language_tags}))
    )
    candidates: list[ClaimCandidate] = []
    for match in SENTENCE_PATTERN.finditer(text):
        sentence: str = match.group(0).strip()
        if len(sentence) < MIN_CLAIM_LENGTH or sentence[-1] in QUESTION_MARKS:
            continue

        topic: ClaimTopic | None = find_topic(sentence, marker_sets)
        if topic is None:
            continue

        candidates.append(
            ClaimCandidate(claim=ClaimText(sentence[:MAX_CLAIM_LENGTH]), topic=topic)
        )
        if len(candidates) == MAX_CLAIMS:
            break

    return candidates


def find_topic(sentence: str, marker_sets: list[ClaimMarkerSet]) -> ClaimTopic | None:
    """The topic of the first marker set the sentence matches."""

    words: list[str] = [fold_word(word) for word in WORD_PATTERN.findall(sentence)]
    spaced: str = f" {' '.join(words)} "
    for marker_set in marker_sets:
        if any(word in marker_set.words for word in words):
            return marker_set.topic

        if any(word.startswith(marker_set.stems) for word in words):
            return marker_set.topic

        if any(phrase_matches(phrase, spaced) for phrase in marker_set.phrases):
            return marker_set.topic

    return None


def phrase_matches(phrase: str, spaced_words: str) -> bool:
    """A phrase, or a phrase whose last word is a stem, among the words."""

    if phrase.endswith(STEM_MARK):
        return f" {phrase.removesuffix(STEM_MARK)}" in spaced_words

    return f" {phrase} " in spaced_words


@cache
def load_marker_sets(language_codes: tuple[str, ...]) -> list[ClaimMarkerSet]:
    """Markers of the languages and English, availability first."""

    codes: list[str] = [ENGLISH_LANGUAGE_CODE, *language_codes]
    marker_sets: list[ClaimMarkerSet] = []
    for topic in (ClaimTopic.AVAILABILITY, ClaimTopic.POLICY):
        markers: list[str] = [
            fold_word(marker)
            for code in dict.fromkeys(codes)
            for marker in CLAIM_MARKERS.get(code, {}).get(topic, ())
        ]
        marker_sets.append(
            ClaimMarkerSet(
                topic=topic,
                words=frozenset(
                    marker
                    for marker in markers
                    if " " not in marker and not marker.endswith(STEM_MARK)
                ),
                stems=tuple(
                    marker.removesuffix(STEM_MARK)
                    for marker in markers
                    if marker.endswith(STEM_MARK)
                ),
                phrases=tuple(marker for marker in markers if " " in marker),
            )
        )

    return marker_sets
