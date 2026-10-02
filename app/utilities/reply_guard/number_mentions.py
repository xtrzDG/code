"""
Finding money amounts, times, dates, phone numbers and other numbers in text.

A written number often has several readings ("19.30" is 19.3, 19:30 or a
date; "1,500" is 1500 or 1.5), so each mention keeps all of them; the guard
accepts a mention when any reading is supported by the evidence. Patterns
work on any script: digits of every numbering system are normalized first,
currency symbols, codes and words and month names come from CLDR.
"""

import re
from decimal import Decimal

from app.utilities.reply_guard.guard_lexicon import GuardLexicon
from app.utilities.reply_guard.number_mention import NumberMention, PartialDate
from app.utilities.reply_guard.number_patterns import (
    CJK_DATE_PATTERN,
    COLON_TIME_PATTERN,
    GROUPED_PHONE_PATTERN,
    H_TIME_PATTERN,
    HOURS_PER_DAY,
    INTERNATIONAL_PHONE_PATTERN,
    ISO_DATE_PATTERN,
    MAX_MINUTE,
    MERIDIEM_TIME_PATTERN,
    MIN_PHONE_DIGITS,
    NOON,
    NOT_DATES,
    NUMBER_PATTERN,
    NUMERIC_DATE_WITH_YEAR_PATTERN,
    SLASH_DATE_PATTERN,
    TRUNK_PHONE_PATTERN,
    TWO_DIGIT_YEAR_CENTURY,
    TWO_GROUP_PHONE_PATTERN,
)
from app.utilities.reply_guard.number_readings import (
    is_thousands_grouping,
    is_valid_date,
)
from app.utilities.reply_guard.numerals import normalize_digits, only_digits
from app.utilities.reply_guard.plain_number_mentions import read_number


def extract_number_mentions(text: str, lexicon: GuardLexicon) -> list[NumberMention]:
    """Every number-bearing mention of a text, in text order."""

    normalized_text: str = normalize_digits(text)
    taken: list[tuple[int, int]] = []
    mentions: list[NumberMention] = []

    def claim(mention: NumberMention | None) -> None:
        if mention is None or overlaps(taken, mention.start, mention.end):
            return

        taken.append((mention.start, mention.end))
        mentions.append(mention)

    for match in ISO_DATE_PATTERN.finditer(normalized_text):
        claim(read_date(text, match, match.group(1), match.group(3), match.group(4)))

    for match in CJK_DATE_PATTERN.finditer(normalized_text):
        claim(read_date(text, match, match.group(1), match.group(2), match.group(3)))

    for match in NUMERIC_DATE_WITH_YEAR_PATTERN.finditer(normalized_text):
        claim(read_numeric_date(text, match, match.group(1), match.group(3)))

    for match in INTERNATIONAL_PHONE_PATTERN.finditer(normalized_text):
        claim(read_phone(text, match))

    for match in COLON_TIME_PATTERN.finditer(normalized_text):
        claim(read_time(text, match, match.group(1), match.group(2), match.group(3)))

    for match in MERIDIEM_TIME_PATTERN.finditer(normalized_text):
        claim(read_time(text, match, match.group(1), None, match.group(2)))

    for match in H_TIME_PATTERN.finditer(normalized_text):
        claim(read_time(text, match, match.group(1), match.group(2), None))

    for match in SLASH_DATE_PATTERN.finditer(normalized_text):
        if match.group(0) not in NOT_DATES:
            claim(read_numeric_date(text, match, match.group(1), match.group(2)))

    for match in GROUPED_PHONE_PATTERN.finditer(normalized_text):
        if not overlaps(taken, match.start(), match.end()):
            claim(read_phone(text, match))

    for pattern in (TWO_GROUP_PHONE_PATTERN, TRUNK_PHONE_PATTERN):
        for match in pattern.finditer(normalized_text):
            if not overlaps(taken, match.start(), match.end()):
                claim(read_phone(text, match))

    for match in NUMBER_PATTERN.finditer(normalized_text):
        if not overlaps(taken, match.start(), match.end()):
            claim(read_number(text, normalized_text, match, lexicon))

    return sorted(mentions, key=lambda mention: mention.start)


def overlaps(taken: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(
        start < taken_end and taken_start < end for taken_start, taken_end in taken
    )


def read_date(
    text: str,
    match: re.Match[str],
    raw_year: str | None,
    raw_month: str,
    raw_day: str,
) -> NumberMention | None:
    year: int | None = None if raw_year is None else int(raw_year)
    month, day = int(raw_month), int(raw_day)
    if not is_valid_date(year, month, day):
        return None

    return NumberMention(
        text=text[match.start() : match.end()],
        start=match.start(),
        end=match.end(),
        dates=frozenset({(year, month, day)}),
    )


def read_numeric_date(
    text: str,
    match: re.Match[str],
    raw_first: str,
    raw_second: str,
) -> NumberMention | None:
    """Day and month in either order ("05.10.2026", "10/5/2026", "5/10")."""

    year: int | None = None
    if match.re is NUMERIC_DATE_WITH_YEAR_PATTERN:
        raw_year: str = match.group(4)
        year = int(raw_year) + (TWO_DIGIT_YEAR_CENTURY if len(raw_year) == 2 else 0)

    first, second = int(raw_first), int(raw_second)
    dates: frozenset[PartialDate] = frozenset(
        (year, month, day)
        for day, month in ((first, second), (second, first))
        if is_valid_date(year, month, day)
    )
    if not dates:
        return None

    return NumberMention(
        text=text[match.start() : match.end()],
        start=match.start(),
        end=match.end(),
        dates=dates,
    )


def read_time(
    text: str,
    match: re.Match[str],
    raw_hour: str,
    raw_minute: str | None,
    meridiem: str | None,
) -> NumberMention | None:
    hour: int = int(raw_hour)
    minute: int = 0 if raw_minute is None else int(raw_minute)
    if meridiem is not None:
        if hour == 0 or hour > NOON:
            return None

        hour = hour % NOON + (NOON if meridiem.lower() == "p" else 0)

    if hour > HOURS_PER_DAY or minute > MAX_MINUTE:
        return None

    return NumberMention(
        text=text[match.start() : match.end()].strip(),
        start=match.start(),
        end=match.end(),
        times=frozenset({(hour % HOURS_PER_DAY, minute)}),
    )


def read_phone(text: str, match: re.Match[str]) -> NumberMention | None:
    """
    A phone number; a grouping that also reads as thousands ("10 500 000")
    keeps that amount as a second reading.
    """

    raw_number: str = match.group(0)
    digits: str = only_digits(raw_number)
    if len(digits) < MIN_PHONE_DIGITS:
        return None

    amounts: frozenset[Decimal] = (
        frozenset({Decimal(digits)})
        if not raw_number.startswith("+") and is_thousands_grouping(raw_number)
        else frozenset()
    )
    return NumberMention(
        text=text[match.start() : match.end()],
        start=match.start(),
        end=match.end(),
        amounts=amounts,
        phone_digits=digits,
    )
