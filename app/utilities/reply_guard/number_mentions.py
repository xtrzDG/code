"""
Finding money amounts, times, dates, phone numbers and other numbers in text.

A written number often has several readings ("19.30" is 19.3, 19:30 or a
date; "1,500" is 1500 or 1.5), so each mention keeps all of them; the guard
accepts a mention when any reading is supported by the evidence. Patterns
work on any script: digits of every numbering system are normalized first,
currency symbols, codes and words and month names come from CLDR.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.utilities.reply_guard.lexicons import GuardLexicon
from app.utilities.reply_guard.numerals import (
    normalize_digits,
    only_digits,
    parse_amount_candidates,
)

type LocalTime = tuple[int, int]
type PartialDate = tuple[int | None, int, int]

SPACE: str = r"[ \t  ]"
# A date or phone never continues a word, a number, a path or a time.
DATE_BOUNDARY: str = r"(?<![\w.,/:+\-])"
# A number may follow a dash ("12-15", "18–25 GEL"), never a word or a path.
NUMBER_BOUNDARY: str = r"(?<![\w.,/:+])"
ISO_DATE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"(\d{4})([-/.])(\d{1,2})\2(\d{1,2})(?!\d)"
)
CJK_DATE_PATTERN: re.Pattern[str] = re.compile(
    r"(?:(\d{4})\s*[年년]\s*)?(\d{1,2})\s*[月월]\s*(\d{1,2})\s*[日일号]"
)
NUMERIC_DATE_WITH_YEAR_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"(\d{1,2})([./\-])(\d{1,2})\2(\d{4}|\d{2})(?![\w]|[.,/\-]\d)"
)
SLASH_DATE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"(\d{1,2})/(\d{1,2})(?![\w/]|[.,]\d)"
)
MERIDIEM: str = SPACE + r"?([ap])\.?" + SPACE + r"?m\b\.?"
COLON_TIME_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY
    + r"(\d{1,2}):([0-5]\d)(?::[0-5]\d)?(?:"
    + MERIDIEM
    + r")?(?![\w:])",
    re.IGNORECASE,
)
MERIDIEM_TIME_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY + r"(1[0-2]|0?[1-9])" + MERIDIEM,
    re.IGNORECASE,
)
H_TIME_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY + r"([01]?\d|2[0-3])h([0-5]\d)?(?![\w])"
)
INTERNATIONAL_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w+])\+\d[\d  \-().]{5,}\d"
)
GROUPED_PHONE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"\(?\d{2,5}\)?(?:[  \-.]\d{2,4}){2,}(?![\w]|[.,]\d)"
)
NUMBER_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY
    + r"(?:\d{1,3}(?:[   .,'’]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?)"
    + r"(?!\d)"
)
DOTTED_TIME_PATTERN: re.Pattern[str] = re.compile(r"^(\d{1,2})\.(\d{2})$")
FOLLOWING_TOKEN_PATTERN: re.Pattern[str] = re.compile(SPACE + r"?([^\s\d]{1,12})")
PRECEDING_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"([^\s\d]{1,12})" + SPACE + r"?$"
)
LEADING_WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+")
# "5 October", "5th of October", "5-го октября", "5. Oktober", "5 de octubre":
# an optional suffix, an optional short connector word, the month, a year.
FOLLOWING_MONTH_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:\.|-?[^\W\d_]{1,3})?"
    + SPACE
    + r"*(?:[^\W\d_]{1,3}"
    + SPACE
    + r"+)?([^\W\d_]+\.?)(?:"
    + SPACE
    + r"*,?"
    + SPACE
    + r"*(\d{4}))?"
)
# "October 5", "Oct. 5th, 2026".
PRECEDING_MONTH_PATTERN: re.Pattern[str] = re.compile(r"([^\W\d_]+)\.?" + SPACE + r"+$")
# A month followed by its own day ("6 on October 5") does not date the number
# before it.
DAY_AFTER_MONTH_PATTERN: re.Pattern[str] = re.compile(
    SPACE + r"*(?:0?[1-9]|[12]\d|3[01])(?!\d)"
)
YEAR_AFTER_DAY_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:st|nd|rd|th|\.)?" + SPACE + r"*,?" + SPACE + r"*(\d{4})"
)
TRAILING_PUNCTUATION: str = ".,;:!?)]}»”\"'"
LEADING_PUNCTUATION: str = "([{«“\"'"
PERCENT_SIGNS: frozenset[str] = frozenset({"%", "٪", "％"})
NOT_DATES: frozenset[str] = frozenset({"24/7"})
MIN_PHONE_DIGITS: int = 7
TWO_DIGIT_YEAR_CENTURY: int = 2000
LEAP_YEAR: int = 2000
NOON: int = 12
HOURS_PER_DAY: int = 24
MAX_DAY: int = 31
MAX_MONTH: int = 12
MAX_MINUTE: int = 59
THOUSANDS_GROUP_LENGTH: int = 3


@dataclass(frozen=True)
class NumberMention:
    """
    One number in a text with every reading it may have (technical record).

    `text` is the mention as written, with its currency, month or meridiem.
    """

    text: str
    start: int
    end: int
    is_money: bool = False
    is_percent: bool = False
    amounts: frozenset[Decimal] = field(default_factory=frozenset[Decimal])
    times: frozenset[LocalTime] = field(default_factory=frozenset[LocalTime])
    dates: frozenset[PartialDate] = field(default_factory=frozenset[PartialDate])
    phone_digits: str | None = None

    @property
    def is_plain_number(self) -> bool:
        """Only a numeric reading: not money, a percentage, time, date or phone."""

        return (
            not self.is_money
            and not self.is_percent
            and not self.times
            and not self.dates
            and self.phone_digits is None
        )


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


def read_number(
    text: str,
    normalized_text: str,
    match: re.Match[str],
    lexicon: GuardLexicon,
) -> NumberMention:
    """
    A number with what surrounds it: a currency before or after makes it
    money, "%" a percentage, a month name a date; "19.30" may also be a time.
    """

    token: str = match.group(0)
    start, end = match.start(), match.end()
    after: str = normalized_text[end:]
    before: str = normalized_text[:start]
    times: set[LocalTime] = set()
    dates: set[PartialDate] = set()
    dotted: re.Match[str] | None = DOTTED_TIME_PATTERN.match(token)
    if dotted is not None:
        first, second = int(dotted.group(1)), int(dotted.group(2))
        if first <= HOURS_PER_DAY and second <= MAX_MINUTE:
            times.add((first % HOURS_PER_DAY, second))

        dates.update(
            (None, month, day)
            for day, month in ((first, second), (second, first))
            if is_valid_date(None, month, day)
        )

    is_money: bool = False
    following: re.Match[str] | None = FOLLOWING_TOKEN_PATTERN.match(after)
    if following is not None and is_currency_token(following.group(1), lexicon):
        is_money = True
        end += following.start(1) + len(
            following.group(1).rstrip(TRAILING_PUNCTUATION) or following.group(1)
        )

    preceding: re.Match[str] | None = PRECEDING_TOKEN_PATTERN.search(before)
    if preceding is not None and is_currency_prefix(
        preceding.group(1),
        before[: preceding.start(1)],
        lexicon,
    ):
        is_money = True
        start = preceding.start(1) + (
            len(preceding.group(1))
            - len(preceding.group(1).lstrip(LEADING_PUNCTUATION))
        )

    amounts: frozenset[Decimal] = parse_amount_candidates(token)
    is_percent: bool = not is_money and after[:1] in PERCENT_SIGNS
    if is_percent:
        end = match.end() + 1
    elif not is_money and token.isdigit() and 1 <= int(token) <= MAX_DAY:
        month_dates: set[PartialDate] = set()
        start, end = read_day_with_month(
            int(token), before, after, match, lexicon, month_dates, (start, end)
        )
        if month_dates:
            # "7 October" is a date only: the day alone proves nothing.
            dates.update(month_dates)
            amounts = frozenset()

    return NumberMention(
        text=text[start:end].strip().rstrip(TRAILING_PUNCTUATION),
        start=start,
        end=end,
        is_money=is_money,
        is_percent=is_percent,
        amounts=amounts,
        times=frozenset(times),
        dates=frozenset(dates),
    )


def read_day_with_month(
    day: int,
    before: str,
    after: str,
    match: re.Match[str],
    lexicon: GuardLexicon,
    dates: set[PartialDate],
    span: tuple[int, int],
) -> tuple[int, int]:
    """Add the dates a day number forms with a neighbouring month name."""

    month_after: re.Match[str] | None = FOLLOWING_MONTH_PATTERN.match(after)
    if month_after is not None and not DAY_AFTER_MONTH_PATTERN.match(
        after[month_after.end(1) :]
    ):
        months: frozenset[int] = lexicon.find_months(month_after.group(1))
        if months:
            year: int | None = (
                None if month_after.group(2) is None else int(month_after.group(2))
            )
            dates.update(
                (year, month, day)
                for month in months
                if is_valid_date(year, month, day)
            )
            return span[0], match.end() + month_after.end()

    month_before: re.Match[str] | None = PRECEDING_MONTH_PATTERN.search(before)
    if month_before is not None:
        months = lexicon.find_months(month_before.group(1))
        if months:
            year_after: re.Match[str] | None = YEAR_AFTER_DAY_PATTERN.match(after)
            year = None if year_after is None else int(year_after.group(1))
            dates.update(
                (year, month, day)
                for month in months
                if is_valid_date(year, month, day)
            )
            end: int = span[1] if year_after is None else match.end() + year_after.end()
            return month_before.start(1), end

    return span


def is_currency_token(raw_token: str, lexicon: GuardLexicon) -> bool:
    """A currency symbol, code or word, with surrounding punctuation tolerated."""

    candidates: list[str] = [
        raw_token,
        raw_token.rstrip(TRAILING_PUNCTUATION),
        raw_token.lstrip(LEADING_PUNCTUATION),
        raw_token.strip(TRAILING_PUNCTUATION + LEADING_PUNCTUATION),
    ]
    word: re.Match[str] | None = LEADING_WORD_PATTERN.match(raw_token)
    if word is not None:
        candidates.append(word.group(0))

    return any(
        candidate != "" and lexicon.is_currency_marker(candidate)
        for candidate in candidates
    )


def is_currency_prefix(
    raw_token: str,
    text_before_token: str,
    lexicon: GuardLexicon,
) -> bool:
    """
    A currency written before its amount ("$18", "GEL 18", "₾ 18"). A marker
    followed by punctuation or right after another number ends that number
    instead ("18 GEL, 20").
    """

    if raw_token.rstrip(TRAILING_PUNCTUATION) != raw_token:
        return False

    if text_before_token.rstrip()[-1:].isdigit():
        return False

    stripped_token: str = raw_token.lstrip(LEADING_PUNCTUATION)
    return any(
        candidate != "" and lexicon.is_currency_marker(candidate)
        for candidate in (raw_token, stripped_token)
    )


def is_thousands_grouping(raw_number: str) -> bool:
    """True for "1 500 000" and "10.500.000"; False for "555 12 34 56"."""

    groups: list[str] = [
        group for group in re.split(r"[  \-.()]+", raw_number) if group != ""
    ]
    return (
        len(groups) > 1
        and 1 <= len(groups[0]) <= THOUSANDS_GROUP_LENGTH
        and all(len(group) == THOUSANDS_GROUP_LENGTH for group in groups[1:])
    )


def is_valid_date(year: int | None, month: int, day: int) -> bool:
    """A real calendar date; without a year, 29 February is allowed."""

    if not (1 <= month <= MAX_MONTH and 1 <= day <= MAX_DAY):
        return False

    try:
        date(LEAP_YEAR if year is None else year, month, day)
    except ValueError:
        return False

    return True
