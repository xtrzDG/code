"""
Cells of exported tables: values as a spreadsheet sorts and sums them
(local times as "YYYY-MM-DD HH:MM" in the business's time zone, amounts
as plain decimals with the currency in its own column, empty for none).
"""

from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from babel.numbers import get_currency_precision
from typed_time_provider import Microseconds

from app.schemas.typings.bookings.constrained_integers import BookingValueMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.privacy.strings import CsvCellText

MICROSECONDS_PER_SECOND: int = 1_000_000
EMPTY: CsvCellText = CsvCellText("")


def text_cell(value: object | None) -> CsvCellText:
    """Any value as its text (an enum by its value); None as an empty cell."""

    if value is None:
        return EMPTY

    if isinstance(value, StrEnum):
        return CsvCellText(value.value)

    return CsvCellText(str(value))


def flag_cell(value: bool) -> CsvCellText:
    return CsvCellText("yes" if value else "no")


def list_cell(values: Iterable[object]) -> CsvCellText:
    """Several values in one cell, separated by "; "."""

    return CsvCellText("; ".join(str(text_cell(value)) for value in values))


def moment_cell(unix_microseconds: Microseconds | None, zone: ZoneInfo) -> CsvCellText:
    """A moment as the local date and time of the business."""

    if unix_microseconds is None:
        return EMPTY

    moment: datetime = datetime.fromtimestamp(
        int(unix_microseconds) / MICROSECONDS_PER_SECOND, tz=UTC
    ).astimezone(zone)
    return CsvCellText(moment.strftime("%Y-%m-%d %H:%M"))


def amount_cell(
    amount_minor: BookingValueMinor | None, currency_code: CurrencyCode | None
) -> CsvCellText:
    """An amount in minor units as a decimal of the currency ("18.00")."""

    if amount_minor is None or currency_code is None:
        return EMPTY

    digits: int = get_currency_precision(currency_code)
    amount: Decimal = Decimal(int(amount_minor)).scaleb(-digits)
    return CsvCellText(f"{amount:.{digits}f}")
