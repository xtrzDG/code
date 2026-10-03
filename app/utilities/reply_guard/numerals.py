"""Digits and numbers as written in any language."""

import unicodedata
from decimal import Decimal, InvalidOperation
from functools import cache

ASCII_DIGITS: str = "0123456789"
# The Arabic decimal and thousands separators written with Arabic-Indic
# digits ("١٫٢٥٠", "١٬٥٠٠") read as "." and ",".
SEPARATOR_REPLACEMENTS: dict[str, str] = {"\u066b": ".", "\u066c": ","}
DECIMAL_MARKS: frozenset[str] = frozenset({".", ","})
THOUSANDS_GROUP_LENGTH: int = 3


def normalize_digits(text: str) -> str:
    """
    Replace every Unicode decimal digit (Arabic-Indic, Persian, Devanagari,
    full-width, ...) with its ASCII digit and the Arabic decimal and
    thousands separators with "." and ","; other characters are kept, so
    positions in the text do not change.
    """

    return "".join(normalize_digit(character) for character in text)


@cache
def normalize_digit(character: str) -> str:
    if character in ASCII_DIGITS:
        return character

    replacement: str | None = SEPARATOR_REPLACEMENTS.get(character)
    if replacement is not None:
        return replacement

    value: int | None = unicodedata.decimal(character, None)
    return character if value is None else ASCII_DIGITS[value]


def parse_amount_candidates(token: str) -> frozenset[Decimal]:
    """
    Values a written number may mean, given that locales swap the decimal
    mark and the thousands separator.

    "1 500" and "1.500.000" group thousands; "1,500.50" and "1.500,50" are
    1500.50; "18,50" is 18.5; a single mark followed by exactly three digits
    ("1,500") is ambiguous and yields both 1500 and 1.5.
    """

    digits_only: str = only_digits(token)
    if digits_only == "":
        return frozenset()

    marks: list[str] = [character for character in token if character in DECIMAL_MARKS]
    if not marks:
        return frozenset({Decimal(digits_only)})

    if len(set(marks)) == 2:
        return frozenset(filter_none([read_decimal(token, marks[-1])]))

    if len(marks) > 1:
        return frozenset({Decimal(digits_only)})

    fraction: str = token.rsplit(marks[0], 1)[1]
    as_decimal: Decimal | None = read_decimal(token, marks[0])
    if len(fraction) == THOUSANDS_GROUP_LENGTH:
        return frozenset(filter_none([as_decimal, Decimal(digits_only)]))

    return frozenset(filter_none([as_decimal]))


def read_decimal(token: str, decimal_mark: str) -> Decimal | None:
    """The token read with `decimal_mark` as the decimal point."""

    integer_part, fraction = token.rsplit(decimal_mark, 1)
    try:
        return Decimal(f"{only_digits(integer_part) or '0'}.{only_digits(fraction)}")
    except InvalidOperation:
        return None


def only_digits(text: str) -> str:
    """ASCII digits of a text (other digits are normalized beforehand)."""

    return "".join(character for character in text if character in ASCII_DIGITS)


def filter_none(values: list[Decimal | None]) -> list[Decimal]:
    return [value for value in values if value is not None]
