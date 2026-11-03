"""
The reply guard's booking check (AI-08): a reply may tell the customer
that a booking is made, confirmed, moved or cancelled only in a turn where
a booking tool succeeded (create_booking, reschedule_booking,
cancel_booking) or where the model looked the booking up
(list_my_bookings). Otherwise the sentence is held back like a policy
claim the facts do not back: the model is asked once to rewrite it, and a
reply that still claims it goes to a colleague.
"""

import re
from collections.abc import Iterable, Sequence
from functools import cache

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import base_language_code
from app.utilities.reply_guard.booking_claim_markers import (
    BOOKING_CLAIM_PHRASES,
    CONDITION_WORDS,
    NEGATION_WORDS,
)
from app.utilities.reply_guard.number_word_lexicon import fold_word

SENTENCE_PATTERN: re.Pattern[str] = re.compile(r"[^.!?؟\n;]+[.!?؟]*")
WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")
QUESTION_MARKS: str = "?؟"
MAX_CLAIM_LENGTH: int = 300
ENGLISH_LANGUAGE_CODE: str = "en"
# Tools whose success backs a statement about a booking's state.
BOOKING_STATE_TOOLS: frozenset[str] = frozenset(
    {
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.RESCHEDULE_BOOKING,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.LIST_MY_BOOKINGS,
    }
)


def has_booking_tool_success(tool_calls: Iterable[ToolCallRecord]) -> bool:
    """A booking tool of this turn succeeded."""

    return any(
        str(call.tool_name) in BOOKING_STATE_TOOLS and not call.is_error
        for call in tool_calls
    )


def find_unbacked_booking_claims(
    text: str,
    language_tags: Iterable[LanguageTag],
    tool_calls: Sequence[ToolCallRecord],
) -> list[str]:
    """
    The sentences that say a booking is done when no booking tool of the
    turn succeeded (none when one did), as written.
    """

    if has_booking_tool_success(tool_calls):
        return []

    codes: tuple[str, ...] = tuple(
        sorted({ENGLISH_LANGUAGE_CODE, *(base_language_code(t) for t in language_tags)})
    )
    phrases, conditions = load_markers(codes)
    claims: list[str] = []
    for match in SENTENCE_PATTERN.finditer(text):
        sentence: str = match.group(0).strip()
        if not sentence or sentence[-1] in QUESTION_MARKS:
            continue

        words: list[str] = [fold_word(word) for word in WORD_PATTERN.findall(sentence)]
        if states_booking(words, phrases, conditions):
            claims.append(sentence[:MAX_CLAIM_LENGTH])

    return claims


def states_booking(
    words: list[str],
    phrases: tuple[tuple[str, ...], ...],
    conditions: tuple[tuple[str, ...], ...],
) -> bool:
    """One of the phrases, not negated, in a sentence with no condition."""

    if any(contains(words, condition) >= 0 for condition in conditions):
        return False

    for phrase in phrases:
        start: int = contains(words, phrase)
        if start >= 0 and (start == 0 or words[start - 1] not in NEGATION_WORDS):
            return True

    return False


def contains(words: list[str], phrase: tuple[str, ...]) -> int:
    """Where the phrase's words start in order among the words; -1 if not."""

    length: int = len(phrase)
    for start in range(len(words) - length + 1):
        if tuple(words[start : start + length]) == phrase:
            return start

    return -1


@cache
def load_markers(
    language_codes: tuple[str, ...],
) -> tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...]]:
    """The folded phrases and condition words of the languages."""

    def split(markers: Iterable[str]) -> tuple[tuple[str, ...], ...]:
        return tuple(
            tuple(fold_word(word) for word in WORD_PATTERN.findall(marker))
            for marker in markers
        )

    return (
        split(
            phrase
            for code in language_codes
            for phrase in BOOKING_CLAIM_PHRASES.get(code, ())
        ),
        split(
            word for code in language_codes for word in CONDITION_WORDS.get(code, ())
        ),
    )
