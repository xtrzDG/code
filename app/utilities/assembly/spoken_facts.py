"""
Facts written the way they are said on the phone (concept section 7).

The fact table is locale-neutral text for the model: "18.00 GEL",
"09:00–13:00", "2026-10-05" and web links. Read aloud as it is, a caller
would hear a currency code, "zero nine colon zero zero" or an address no one
can type while driving. The phone instruction gets the same rows with
prices as "18 Georgian laris", hours as "from 9:00 to 13:00", dates as
"5 October 2026" and no links: a row that is only a link is left out and
named instead, a link inside a text becomes a short note. The results are
plain text for the instruction, not facts: the version keeps its facts.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from babel.numbers import get_currency_name

from app.schemas.domain.assistants import BusinessFact
from app.utilities.conversations.untrusted_text import wrap_untrusted

MONEY_PATTERN: re.Pattern[str] = re.compile(r"(?<![\w.,])(\d+(?:\.\d+)?) ([A-Z]{3})\b")
TIME_RANGE_PATTERN: re.Pattern[str] = re.compile(
    r"\b(\d{2}:\d{2})\s*[–-]\s*(\d{2}:\d{2})\b"
)
TIME_PATTERN: re.Pattern[str] = re.compile(r"\b(\d{2}):(\d{2})\b")
ISO_DATE_PATTERN: re.Pattern[str] = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
URL_PATTERN: re.Pattern[str] = re.compile(r"https?://\S+|www\.\S+")
LINK_NOTE: str = "(a link, never read it aloud)"
ALL_DAY_RANGE: tuple[str, str] = ("00:00", "24:00")
MIDNIGHT_TIMES: frozenset[str] = frozenset({"00:00", "24:00"})
SPOKEN_LOCALE: str = "en"
MONTH_NAMES: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@dataclass(frozen=True)
class SpokenFactTable:
    """
    Rows of the phone instruction (label, value) and the labels of rows that
    were only a link (technical record).
    """

    rows: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])
    link_labels: list[str] = field(default_factory=list[str])


def speak_facts(facts: Sequence[BusinessFact]) -> SpokenFactTable:
    """The fact rows as they are said on the phone; link rows are named only."""

    table = SpokenFactTable()
    for fact in facts:
        value: str = str(fact.value).strip()
        if URL_PATTERN.fullmatch(value) is not None:
            table.link_labels.append(str(fact.label))
            continue

        spoken_value: str = speak_text(value)
        table.rows.append(
            (
                speak_text(str(fact.label)),
                wrap_untrusted(spoken_value) if fact.is_imported else spoken_value,
            )
        )

    return table


def speak_text(text: str) -> str:
    """Links, prices, dates and times of a text in their spoken form."""

    spoken: str = URL_PATTERN.sub(LINK_NOTE, text)
    spoken = MONEY_PATTERN.sub(speak_money, spoken)
    spoken = ISO_DATE_PATTERN.sub(speak_date, spoken)
    spoken = TIME_RANGE_PATTERN.sub(speak_time_range, spoken)
    return TIME_PATTERN.sub(speak_time, spoken)


def speak_money(match: re.Match[str]) -> str:
    """ "18.00 GEL" -> "18 Georgian laris"; an unknown code is left as it is."""

    amount_text: str = match.group(1)
    currency_code: str = match.group(2)
    amount: Decimal = Decimal(amount_text)
    is_whole: bool = amount == amount.to_integral_value()
    # "1.00" counts as plural in English; a whole amount is said as "1".
    spoken_amount: str = str(int(amount)) if is_whole else amount_text
    currency_name: str = get_currency_name(
        currency_code,
        count=int(amount) if is_whole else amount,
        locale=SPOKEN_LOCALE,
    )
    if currency_name == currency_code:
        return match.group(0)

    return f"{spoken_amount} {currency_name}"


def speak_date(match: re.Match[str]) -> str:
    """ "2026-10-05" -> "5 October 2026"; an impossible month stays as it is."""

    year, month, day = (int(group) for group in match.groups())
    if not 1 <= month <= len(MONTH_NAMES):
        return match.group(0)

    return f"{day} {MONTH_NAMES[month - 1]} {year}"


def speak_time_range(match: re.Match[str]) -> str:
    """ "09:00–13:00" -> "from 9:00 to 13:00"; a whole day -> "around the clock"."""

    opens_at, closes_at = match.group(1), match.group(2)
    if (opens_at, closes_at) == ALL_DAY_RANGE:
        return "around the clock"

    return f"from {say_time(opens_at)} to {say_time(closes_at)}"


def speak_time(match: re.Match[str]) -> str:
    return say_time(match.group(0))


def say_time(time_text: str) -> str:
    """ "09:30" -> "9:30", "00:00" and "24:00" -> "midnight"."""

    if time_text in MIDNIGHT_TIMES:
        return "midnight"

    hours, minutes = time_text.split(":")
    return f"{int(hours)}:{minutes}"
