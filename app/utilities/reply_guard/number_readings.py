"""Checks shared by the readings of a number: calendar dates, digit groups."""

import re
from datetime import date

from app.utilities.reply_guard.number_patterns import (
    LEAP_YEAR,
    MAX_DAY,
    MAX_MONTH,
    THOUSANDS_GROUP_LENGTH,
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
