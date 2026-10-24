"""
Exact arithmetic of exchange rates: decimal strings in, decimal strings out.

Rates are `Decimal`s built from their decimal strings, never binary floats.
A computed rate (an inverse, a cross rate) is rounded once, half to even, to
12 digits after the point; one that would round to zero is refused.
"""

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from app.schemas.typings.billing.constrained_integers import ExchangeRateDayNumber
from app.schemas.typings.billing.constrained_strings import (
    CurrencyPairCode,
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode

RATE_STEP: Decimal = Decimal("1e-12")
MAX_RATE: Decimal = Decimal("999999999999")
ONE: Decimal = Decimal(1)


def read_rate(value: ExchangeRateValue) -> Decimal:
    """The exact number of a stored rate."""

    return Decimal(str(value))


def build_rate(amount: Decimal) -> ExchangeRateValue | None:
    """
    A computed rate as a stored one: rounded half to even to 12 places,
    trailing zeros dropped; None when it is not a positive finite number
    that fits (it would round to zero, or overflow).
    """

    try:
        rounded: Decimal = amount.quantize(RATE_STEP, rounding=ROUND_HALF_EVEN)
    except InvalidOperation:
        return None

    if not rounded.is_finite() or rounded <= 0 or rounded > MAX_RATE:
        return None

    text: str = format(rounded.normalize(), "f")
    return ExchangeRateValue(text)


def parse_rate_text(text: str, per_units: int = 1) -> ExchangeRateValue | None:
    """
    A rate as a feed prints it ("2.9552"; NBG: per `per_units` units, e.g.
    100 AMD = "0.6884" GEL); None when it is not a positive number.
    """

    try:
        amount: Decimal = Decimal(text.strip())
    except InvalidOperation:
        return None

    if per_units < 1 or not amount.is_finite():
        return None

    return build_rate(amount / Decimal(per_units))


def invert_rate(rate: ExchangeRateValue) -> ExchangeRateValue | None:
    """quote -> base from base -> quote: 1 / rate."""

    return build_rate(ONE / read_rate(rate))


def divide_rates(
    numerator: ExchangeRateValue, denominator: ExchangeRateValue
) -> ExchangeRateValue | None:
    """
    A cross rate through a pivot: B -> C = (P -> C) / (P -> B), e.g.
    USD -> AMD = (EUR -> AMD) / (EUR -> USD).
    """

    return build_rate(read_rate(numerator) / read_rate(denominator))


def pair_code(base: CurrencyCode, quote: CurrencyCode) -> CurrencyPairCode:
    return CurrencyPairCode(f"{base}/{quote}")


def rate_day_number(rate_date: ExchangeRateDate) -> ExchangeRateDayNumber:
    """2026-09-30 -> 20260930 (the newest rate sorts last)."""

    return ExchangeRateDayNumber(int(str(rate_date).replace("-", "")))


def days_between(rate_date: ExchangeRateDate, today: date) -> int:
    return (today - date.fromisoformat(str(rate_date))).days


def older_date(first: ExchangeRateDate, second: ExchangeRateDate) -> ExchangeRateDate:
    """The date a rate computed from two rates is as old as."""

    return first if str(first) <= str(second) else second
