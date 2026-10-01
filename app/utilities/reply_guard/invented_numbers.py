"""
Invented-numbers guard (concept section 5, "Защита от выдуманных цифр").

Every money amount, time, date, phone number and other number in an
assistant reply must appear in the evidence: the version's facts, the tool
results, the customer's messages and the server-written context. Small
counts (0 to 10) written as plain numbers are not checked, since "2 guests"
or "1 table" invent nothing; small prices, percentages, times and dates are.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.reply_guard.lexicons import GuardLexicon, build_guard_lexicon
from app.utilities.reply_guard.number_mentions import (
    MIN_PHONE_DIGITS,
    NOON,
    LocalTime,
    NumberMention,
    PartialDate,
    extract_number_mentions,
)

MAX_UNCHECKED_COUNT: Decimal = Decimal(10)
# National and international forms of a phone share their last nine digits.
PHONE_SUFFIX_LENGTH: int = 9


@dataclass(frozen=True)
class EvidenceIndex:
    """
    Every value the evidence supports (technical record).

    `amounts` are numbers written as numbers (prices, counts, years);
    `date_time_parts` are hours, minutes, days, months and years of dates
    and times, which support a plain number but never a price.
    """

    amounts: frozenset[Decimal] = field(default_factory=frozenset[Decimal])
    date_time_parts: frozenset[Decimal] = field(default_factory=frozenset[Decimal])
    times: frozenset[LocalTime] = field(default_factory=frozenset[LocalTime])
    dates: frozenset[PartialDate] = field(default_factory=frozenset[PartialDate])
    digit_strings: frozenset[str] = field(default_factory=frozenset[str])


def find_unverified_values(
    reply: MessageText,
    evidence_texts: Iterable[str],
    language_tags: Iterable[LanguageTag],
    currency_codes: Iterable[CurrencyCode],
) -> list[UnverifiedReplyValue]:
    """
    Values of the reply that no evidence supports, as written, in reply
    order and without repeats. An empty list means the reply may be sent.
    """

    lexicon: GuardLexicon = build_guard_lexicon(language_tags, currency_codes)
    index: EvidenceIndex = build_evidence_index(evidence_texts, lexicon)
    unverified_values: list[UnverifiedReplyValue] = []
    for mention in extract_number_mentions(str(reply), lexicon):
        if is_unchecked_count(mention) or is_supported(mention, index):
            continue

        value = UnverifiedReplyValue(mention.text)
        if value not in unverified_values:
            unverified_values.append(value)

    return unverified_values


def build_evidence_index(
    evidence_texts: Iterable[str],
    lexicon: GuardLexicon,
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
    for evidence_text in evidence_texts:
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

    return EvidenceIndex(
        amounts=frozenset(amounts),
        date_time_parts=frozenset(date_time_parts),
        times=frozenset(times),
        dates=frozenset(dates),
        digit_strings=frozenset(digit_strings),
    )


def is_unchecked_count(mention: NumberMention) -> bool:
    return mention.is_plain_number and all(
        amount == amount.to_integral_value() and 0 <= amount <= MAX_UNCHECKED_COUNT
        for amount in mention.amounts
    )


def is_supported(mention: NumberMention, index: EvidenceIndex) -> bool:
    """
    True when any reading is in the evidence. Prices and percentages must
    match a number of the evidence; a plain number may also match a part of
    an evidence date or time ("the 5th" and "2026-10-05").
    """

    supporting_amounts: frozenset[Decimal] = (
        index.amounts
        if mention.is_money or mention.is_percent
        else index.amounts | index.date_time_parts
    )
    if mention.amounts & supporting_amounts or mention.times & index.times:
        return True

    if any(is_time_supported(time, index) for time in mention.times):
        return True

    if any(is_date_supported(date, index) for date in mention.dates):
        return True

    return mention.phone_digits is not None and is_phone_supported(
        mention.phone_digits, index
    )


def is_time_supported(time: LocalTime, index: EvidenceIndex) -> bool:
    """
    A full hour is supported by the bare hour number ("at 7" supports
    "19:00" and "7 pm").
    """

    hour, minute = time
    if minute != 0:
        return False

    hour_readings: set[Decimal] = {Decimal(hour)}
    if hour > NOON:
        hour_readings.add(Decimal(hour - NOON))

    return bool(hour_readings & index.amounts)


def is_date_supported(date: PartialDate, index: EvidenceIndex) -> bool:
    year, month, day = date
    return any(
        evidence_month == month
        and evidence_day == day
        and (year is None or evidence_year is None or evidence_year == year)
        for evidence_year, evidence_month, evidence_day in index.dates
    )


def is_phone_supported(phone_digits: str, index: EvidenceIndex) -> bool:
    suffix: str = phone_digits[-PHONE_SUFFIX_LENGTH:]
    return any(
        phone_digits in evidence_digits
        or (
            len(phone_digits) >= PHONE_SUFFIX_LENGTH
            and evidence_digits.endswith(suffix)
        )
        for evidence_digits in index.digit_strings
    )
