"""
A plain number with what surrounds it: a currency makes it money, "%" a
percentage, a neighbouring month name a date; "19.30" may also be a time.
"""

import re
from decimal import Decimal

from app.utilities.reply_guard.guard_lexicon import GuardLexicon
from app.utilities.reply_guard.number_mention import (
    LocalTime,
    NumberMention,
    PartialDate,
)
from app.utilities.reply_guard.number_patterns import (
    DAY_AFTER_MONTH_PATTERN,
    DOTTED_TIME_PATTERN,
    FOLLOWING_MONTH_PATTERN,
    FOLLOWING_TOKEN_PATTERN,
    HOURS_PER_DAY,
    LEADING_PUNCTUATION,
    LEADING_WORD_PATTERN,
    MAX_DAY,
    MAX_MINUTE,
    PERCENT_SIGNS,
    PRECEDING_MONTH_PATTERN,
    PRECEDING_TOKEN_PATTERN,
    TRAILING_PUNCTUATION,
    YEAR_AFTER_DAY_PATTERN,
)
from app.utilities.reply_guard.number_readings import is_valid_date
from app.utilities.reply_guard.numerals import parse_amount_candidates


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
