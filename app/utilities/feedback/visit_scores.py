"""
Reading a visit rating (1 to 5) from a customer's reply to a feedback
request: a digit in any script ("5", "٥", "５", "5️⃣"), "4/5" and "4 out of
5", star emoji ("⭐⭐⭐⭐", "★★★☆☆"), or the number written out in the
customer's language or English ("five", "пятёрка", "ხუთი"), alone or
followed by a comment ("5, all great", "4 stars - the coffee was cold").

A message whose rating is unclear is not a rating: a second number ("2
people at 7"), a question, a decimal ("4.5"), a number outside 1 to 5 or
a long text go to the assistant instead.
"""

import re
import unicodedata
from collections.abc import Iterable

from app.schemas.typings.feedback.constrained_integers import VisitScore
from app.utilities.feedback.visit_score_words import (
    NUMBER_WORDS,
    OUT_OF_WORDS,
    SCORE_UNIT_PREFIXES,
)

MAX_RATING_MESSAGE_LENGTH: int = 300
MIN_SCORE: int = 1
MAX_SCORE: int = 5
FILLED_STARS: frozenset[str] = frozenset({"⭐", "★", "\U0001f31f"})
EMPTY_STARS: frozenset[str] = frozenset({"☆"})
# Marks that dress an emoji or a keycap ("5️⃣") without changing it.
PRESENTATION_MARKS: tuple[str, ...] = ("️", "︎", "⃣")
QUESTION_MARKS: frozenset[str] = frozenset({"?", "？", "؟", ";"})
FALLBACK_LANGUAGE: str = "en"
OUT_OF_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(?:/|(?:" + "|".join(re.escape(word) for word in OUT_OF_WORDS) + r")\s)\s*5"
)
LEADING_DIGITS: re.Pattern[str] = re.compile(r"^(\d+)")


def normalize_rating_text(text: str) -> str:
    """NFKC, lower case, digits of every script as ASCII, no emoji marks."""

    normalized: str = unicodedata.normalize("NFKC", text).casefold()
    for mark in PRESENTATION_MARKS:
        normalized = normalized.replace(mark, "")

    return "".join(ascii_digit(character) for character in normalized).strip()


def ascii_digit(character: str) -> str:
    value: int | None = unicodedata.decimal(character, None)
    if value is None or character.isascii():
        return character

    return str(value)


def parse_visit_score(text: str, languages: Iterable[str]) -> VisitScore | None:
    """
    The rating a reply gives, or None. `languages` are the base languages
    whose number words count (the conversation's); English always does.
    """

    if len(text) > MAX_RATING_MESSAGE_LENGTH:
        return None

    normalized: str = normalize_rating_text(text)
    if normalized == "" or any(mark in normalized for mark in QUESTION_MARKS):
        return None

    stars: int | None = count_stars(normalized)
    if stars is not None:
        return VisitScore(stars) if MIN_SCORE <= stars <= MAX_SCORE else None

    number, rest, is_word = read_leading_number(normalized, languages)
    if number is None or not MIN_SCORE <= number <= MAX_SCORE:
        return None

    rest = strip_out_of_five(rest)
    if any(character.isdigit() for character in rest) or not starts_apart(
        rest, is_word
    ):
        return None

    return VisitScore(number)


def count_stars(text: str) -> int | None:
    """
    The filled stars of a rating made of stars ("⭐⭐⭐⭐", "★★★☆☆ good");
    None when the text has none, or digits besides them.
    """

    filled: int = sum(1 for character in text if character in FILLED_STARS)
    if filled == 0 or any(character.isdigit() for character in text):
        return None

    return filled


def read_leading_number(
    text: str, languages: Iterable[str]
) -> tuple[int | None, str, bool]:
    """
    The number the text starts with, what follows it, and whether it was
    written as a word (digits first, then the longest number word).
    """

    digits: re.Match[str] | None = LEADING_DIGITS.match(text)
    if digits is not None:
        return int(digits.group(1)), text[digits.end() :], False

    best: tuple[int | None, str, bool] = (None, text, True)
    longest: int = 0
    for language in sorted({*languages, FALLBACK_LANGUAGE}):
        for index, forms in enumerate(NUMBER_WORDS.get(language, ())):
            for word in forms.split("|"):
                if len(word) > longest and starts_with_word(text, word):
                    best, longest = (index + 1, text[len(word) :], True), len(word)

    return best


def starts_with_word(text: str, word: str) -> bool:
    """`word` begins the text and is not the start of a longer word."""

    if not text.startswith(word):
        return False

    following: str = text[len(word) : len(word) + 1]
    return following == "" or not following.isalpha() or is_ideographic(word)


def is_ideographic(word: str) -> bool:
    """Chinese and Japanese numerals run into the next word ("五星")."""

    return all(unicodedata.east_asian_width(character) == "W" for character in word)


def strip_out_of_five(rest: str) -> str:
    """ "4/5", "4 из 5", "4 out of 5": the "of 5" part removed."""

    out_of: re.Match[str] | None = OUT_OF_PATTERN.match(rest)
    return rest if out_of is None else rest[out_of.end() :]


def starts_apart(rest: str, is_word: bool) -> bool:
    """
    What follows the rating is nothing, a unit ("stars", "баллов"), or a
    comment set apart by punctuation or emoji ("five, all great"); after
    digits a space is enough ("5 all great"), after a word it is not
    ("one more thing", "two of us tomorrow" are sentences).
    """

    comment: str = rest.lstrip()
    if comment == "" or any(comment.startswith(unit) for unit in SCORE_UNIT_PREFIXES):
        return True

    if not comment[0].isalnum():
        return True

    return not is_word and rest[0].isspace()
