"""
The reply guard's booking check (AI-08): a reply may tell the customer
that a booking is made, confirmed, moved or cancelled only in a turn where
a booking tool succeeded (create_booking, reschedule_booking,
cancel_booking) or where the model looked the booking up
(list_my_bookings). A later reply may repeat what an earlier tool call of
the conversation did, of the same kind only: "your table is confirmed"
after an earlier create_booking (or reschedule or look-up), "it is
cancelled" after an earlier cancel_booking, "it was moved" after an
earlier reschedule_booking; an earlier booking never backs a cancellation
or a move. Otherwise the sentence is held back like a policy claim the
facts do not back: the model is asked once to rewrite it, and a reply that
still claims it goes to a colleague.
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
# Word beginnings (folded) that make a claim phrase say a booking was
# cancelled or moved; every other phrase says one is made or confirmed.
CANCEL_STEMS: tuple[str, ...] = (
    "cancel",
    "annul",
    "anul",
    "storn",
    "abgesagt",
    "отмен",
    "скас",
    "გაუქმ",
    "გავაუქმ",
)
MOVE_STEMS: tuple[str, ...] = (
    "resched",
    "moved",
    "spostat",
    "verschoben",
    "déplac",
    "cambi",
    "movid",
    "перенес",
    "გადატან",
    "გადავიტან",
    "გადაგიტან",
)
CANCELLED: str = "cancelled"
MOVED: str = "moved"
BOOKED: str = "booked"
# The tools whose success earlier in the conversation backs a claim of each
# kind repeated in a later reply.
EARLIER_BACKING: dict[str, frozenset[str]] = {
    CANCELLED: frozenset({AssistantToolName.CANCEL_BOOKING}),
    MOVED: frozenset({AssistantToolName.RESCHEDULE_BOOKING}),
    BOOKED: frozenset(
        {
            AssistantToolName.CREATE_BOOKING,
            AssistantToolName.RESCHEDULE_BOOKING,
            AssistantToolName.LIST_MY_BOOKINGS,
        }
    ),
}


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
    earlier_calls: Sequence[ToolCallRecord] = (),
) -> list[str]:
    """
    The sentences that say a booking is done when no booking tool of the
    turn succeeded (none when one did), as written; `earlier_calls` (the
    conversation's stored tool calls) back a repeated claim of their kind.
    """

    if has_booking_tool_success(tool_calls):
        return []

    earlier_tools: frozenset[str] = frozenset(
        str(call.tool_name) for call in earlier_calls if not call.is_error
    )
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
        kinds: set[str] = claimed_kinds(words, phrases, conditions)
        if any(not EARLIER_BACKING[kind] & earlier_tools for kind in kinds):
            claims.append(sentence[:MAX_CLAIM_LENGTH])

    return claims


def claimed_kinds(
    words: list[str],
    phrases: tuple[tuple[str, ...], ...],
    conditions: tuple[tuple[str, ...], ...],
) -> set[str]:
    """
    What the sentence says is done (booked, moved, cancelled): its phrases
    that are not negated; none in a sentence with a condition.
    """

    if any(contains(words, condition) >= 0 for condition in conditions):
        return set()

    kinds: set[str] = set()
    for phrase in phrases:
        start: int = contains(words, phrase)
        if start >= 0 and (start == 0 or words[start - 1] not in NEGATION_WORDS):
            kinds.add(kind_of(phrase))

    return kinds


def kind_of(phrase: tuple[str, ...]) -> str:
    """CANCELLED, MOVED or BOOKED: what a claim phrase says was done."""

    if any(word.startswith(CANCEL_STEMS) for word in phrase):
        return CANCELLED

    if any(word.startswith(MOVE_STEMS) for word in phrase):
        return MOVED

    return BOOKED


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
