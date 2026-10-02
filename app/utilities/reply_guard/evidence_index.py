"""What the evidence of a reply says: every reading of every number in it."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from app.utilities.reply_guard.guard_lexicon import GuardLexicon
from app.utilities.reply_guard.hour_words import HOUR_PREFIX_WORDS, HOUR_SUFFIX_WORDS
from app.utilities.reply_guard.number_mention import (
    LocalTime,
    NumberMention,
    PartialDate,
)
from app.utilities.reply_guard.number_mentions import extract_number_mentions
from app.utilities.reply_guard.number_patterns import HOURS_PER_DAY, MIN_PHONE_DIGITS
from app.utilities.reply_guard.numerals import normalize_digits

HOUR_CONTEXT_PUNCTUATION: str = ".,;:!?()[]«»\"'’“”-–"


@dataclass(frozen=True)
class EvidenceIndex:
    """
    Every value the evidence supports (technical record).

    `amounts` are numbers written as numbers (prices, counts, years);
    `date_time_parts` are hours, minutes, days, months and years of dates
    and times, which support a plain number but never a price;
    `hour_hints` are bare numbers written as clock hours ("at 7").
    """

    amounts: frozenset[Decimal] = field(default_factory=frozenset[Decimal])
    date_time_parts: frozenset[Decimal] = field(default_factory=frozenset[Decimal])
    times: frozenset[LocalTime] = field(default_factory=frozenset[LocalTime])
    dates: frozenset[PartialDate] = field(default_factory=frozenset[PartialDate])
    digit_strings: frozenset[str] = field(default_factory=frozenset[str])
    hour_hints: frozenset[int] = field(default_factory=frozenset[int])


def build_evidence_index(
    evidence_texts: Iterable[str],
    lexicon: GuardLexicon,
    is_reading_hour_hints: bool = False,
) -> EvidenceIndex:
    """
    Readings of every mention in the evidence. Parts of dates and times
    count as numbers too, so "the 5th" is supported by "2026-10-05".
    """

    amounts: set[Decimal] = set()
    date_time_parts: set[Decimal] = set()
    times: set[LocalTime] = set()
    dates: set[PartialDate] = set()
    digit_strings: set[str] = set()
    hour_hints: set[int] = set()
    for evidence_text in evidence_texts:
        normalized_text: str = normalize_digits(evidence_text)
        for mention in extract_number_mentions(evidence_text, lexicon):
            amounts.update(mention.amounts)
            times.update(mention.times)
            dates.update(mention.dates)
            for hour, minute in mention.times:
                date_time_parts.update({Decimal(hour), Decimal(minute)})

            for year, month, day in mention.dates:
                date_time_parts.update({Decimal(month), Decimal(day)})
                if year is not None:
                    date_time_parts.add(Decimal(year))

            if mention.phone_digits is not None:
                digit_strings.add(mention.phone_digits)

            for amount in mention.amounts:
                if amount == amount.to_integral_value() and amount >= 0:
                    digits: str = str(int(amount))
                    if len(digits) >= MIN_PHONE_DIGITS:
                        digit_strings.add(digits)

            hour_hint: int | None = read_hour_hint(mention, normalized_text)
            if is_reading_hour_hints and hour_hint is not None:
                hour_hints.add(hour_hint)

    return EvidenceIndex(
        amounts=frozenset(amounts),
        date_time_parts=frozenset(date_time_parts),
        times=frozenset(times),
        dates=frozenset(dates),
        digit_strings=frozenset(digit_strings),
        hour_hints=frozenset(hour_hints),
    )


def read_hour_hint(mention: NumberMention, normalized_text: str) -> int | None:
    """
    The clock hour a bare number names when it is written as one: after
    "at", "в", "um" and the like, or before "o'clock", "часов", "-ზე".
    """

    if not mention.is_plain_number or len(mention.amounts) != 1:
        return None

    value: Decimal = next(iter(mention.amounts))
    if value != value.to_integral_value() or not 0 <= value <= HOURS_PER_DAY:
        return None

    before_words: list[str] = normalized_text[: mention.start].split()
    after_words: list[str] = normalized_text[mention.end :].split()
    preceding: str = (
        before_words[-1].lower().strip(HOUR_CONTEXT_PUNCTUATION) if before_words else ""
    )
    following: str = (
        after_words[0].lower().strip(HOUR_CONTEXT_PUNCTUATION) if after_words else ""
    )
    if preceding in HOUR_PREFIX_WORDS or following in HOUR_SUFFIX_WORDS:
        return int(value)

    return None
