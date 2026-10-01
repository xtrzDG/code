"""
Invented-numbers guard (concept section 5, "Защита от выдуманных цифр").

Every money amount, time, date, phone number and other number in an
assistant reply must appear in the evidence. Trusted evidence is what the
business and the server said: the version's facts, tool results and the
server-written context. Customer evidence is what the customer wrote (and
what the assistant already repeated from it): it may back times, dates,
phone numbers and counts the customer gave, but never a price or a
percentage (concept: a price comes only from get_price or the facts), and
a bare hour backs a full-hour time only when the customer wrote it as an
hour ("at 7" backs "19:00"; "table for 7" does not). Small counts (0 to 10)
written as plain numbers are not checked, since "2 guests" or "1 table"
invent nothing; small prices, percentages, times and dates are.
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
from app.utilities.reply_guard.lexicons import (
    HOUR_PREFIX_WORDS,
    HOUR_SUFFIX_WORDS,
    GuardLexicon,
    build_guard_lexicon,
)
from app.utilities.reply_guard.number_mentions import (
    HOURS_PER_DAY,
    MIN_PHONE_DIGITS,
    NOON,
    LocalTime,
    NumberMention,
    PartialDate,
    extract_number_mentions,
)
from app.utilities.reply_guard.numerals import normalize_digits

MAX_UNCHECKED_COUNT: Decimal = Decimal(10)
# National and international forms of a phone share their last nine digits.
PHONE_SUFFIX_LENGTH: int = 9
NATIONAL_TRUNK_PREFIX: str = "0"
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


def find_unverified_values(
    reply: MessageText,
    evidence_texts: Iterable[str],
    language_tags: Iterable[LanguageTag],
    currency_codes: Iterable[CurrencyCode],
    customer_texts: Iterable[str] = (),
) -> list[UnverifiedReplyValue]:
    """
    Values of the reply that no evidence supports, as written, in reply
    order and without repeats. An empty list means the reply may be sent.

    `evidence_texts` are trusted (facts, tool results, server context);
    `customer_texts` are what the customer wrote, which never backs money.
    """

    lexicon: GuardLexicon = build_guard_lexicon(language_tags, currency_codes)
    trusted: EvidenceIndex = build_evidence_index(evidence_texts, lexicon)
    customer_text_list: list[str] = list(customer_texts)
    customer: EvidenceIndex = build_evidence_index(
        customer_text_list,
        lexicon,
        is_reading_hour_hints=True,
    )
    unverified_values: list[UnverifiedReplyValue] = []
    for mention in extract_number_mentions(str(reply), lexicon):
        if is_unchecked_count(mention) or is_supported(mention, trusted, customer):
            continue

        value = UnverifiedReplyValue(mention.text)
        if value not in unverified_values:
            unverified_values.append(value)

    return unverified_values


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


def is_unchecked_count(mention: NumberMention) -> bool:
    return mention.is_plain_number and all(
        amount == amount.to_integral_value() and 0 <= amount <= MAX_UNCHECKED_COUNT
        for amount in mention.amounts
    )


def is_supported(
    mention: NumberMention,
    trusted: EvidenceIndex,
    customer: EvidenceIndex | None = None,
) -> bool:
    """
    True when any reading is in the evidence. Prices and percentages must
    match a number of the trusted evidence; a plain number may also match a
    number the customer wrote or a part of an evidence date or time ("the
    5th" and "2026-10-05").
    """

    other: EvidenceIndex = customer if customer is not None else EvidenceIndex()
    supporting_amounts: frozenset[Decimal] = (
        trusted.amounts
        if mention.is_money or mention.is_percent
        else trusted.amounts
        | trusted.date_time_parts
        | other.amounts
        | other.date_time_parts
    )
    times: frozenset[LocalTime] = trusted.times | other.times
    if mention.amounts & supporting_amounts or mention.times & times:
        return True

    hour_hints: frozenset[int] = trusted.hour_hints | other.hour_hints
    if any(is_time_supported(time, hour_hints) for time in mention.times):
        return True

    dates: frozenset[PartialDate] = trusted.dates | other.dates
    if any(is_date_supported(date, dates) for date in mention.dates):
        return True

    digit_strings: frozenset[str] = trusted.digit_strings | other.digit_strings
    if mention.phone_digits is not None:
        return is_phone_supported(mention.phone_digits, digit_strings)

    return mention.is_plain_number and any(
        amount == amount.to_integral_value()
        and len(str(int(amount))) >= MIN_PHONE_DIGITS
        and is_phone_supported(str(int(amount)), digit_strings)
        for amount in mention.amounts
        if amount >= 0
    )


def is_time_supported(time: LocalTime, hour_hints: frozenset[int]) -> bool:
    """
    A full hour is supported by a bare hour the customer wrote as an hour
    ("at 7" supports "19:00" and "7 pm").
    """

    hour, minute = time
    if minute != 0:
        return False

    hour_readings: set[int] = {hour}
    if hour > NOON:
        hour_readings.add(hour - NOON)

    return bool(hour_readings & hour_hints)


def is_date_supported(date: PartialDate, dates: frozenset[PartialDate]) -> bool:
    year, month, day = date
    return any(
        evidence_month == month
        and evidence_day == day
        and (year is None or evidence_year is None or evidence_year == year)
        for evidence_year, evidence_month, evidence_day in dates
    )


def is_phone_supported(phone_digits: str, digit_strings: frozenset[str]) -> bool:
    """
    The same phone in the evidence, written in any form: with or without the
    country calling code or a national trunk "0" ("03-123-4567" and
    "+972 3-123-4567", "2222 3333" and "+965 2222 3333"). The shorter number
    must still have at least seven digits.
    """

    reply_forms: set[str] = {phone_digits, strip_trunk_prefix(phone_digits)}
    suffix: str = phone_digits[-PHONE_SUFFIX_LENGTH:]
    for evidence_digits in digit_strings:
        if phone_digits in evidence_digits or (
            len(phone_digits) >= PHONE_SUFFIX_LENGTH
            and evidence_digits.endswith(suffix)
        ):
            return True

        evidence_forms: set[str] = {
            evidence_digits,
            strip_trunk_prefix(evidence_digits),
        }
        for reply_form in reply_forms:
            for evidence_form in evidence_forms:
                shorter, longer = sorted((reply_form, evidence_form), key=len)
                if len(shorter) >= MIN_PHONE_DIGITS and longer.endswith(shorter):
                    return True

    return False


def strip_trunk_prefix(digits: str) -> str:
    """A national number without its trunk "0" ("0322123456" -> "322123456")."""

    return digits.removeprefix(NATIONAL_TRUNK_PREFIX)
