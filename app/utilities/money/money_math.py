"""
Exact money arithmetic on minor units with Decimal.

Minor-unit precision comes from CLDR (Babel): EUR and GEL 2, JPY 0, KWD 3.
Every result is rounded once to the precision of its currency: prices half
up, conversions between currencies half to even (no drift either way over
many conversions).
"""

from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from babel.numbers import get_currency_precision

from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import (
    CurrencyMinorUnitDigits,
    DiscountPercent,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.constrained_strings import ExchangeRateValue
from app.schemas.typings.localization.constrained_strings import CurrencyCode

WHOLE_MINOR_UNIT: Decimal = Decimal(1)
ONE_HUNDRED_PERCENT: Decimal = Decimal(100)


def get_currency_minor_unit_digits(
    currency_code: CurrencyCode,
) -> CurrencyMinorUnitDigits:
    """Digits after the decimal point of a currency (unknown codes: 2)."""

    return CurrencyMinorUnitDigits(get_currency_precision(str(currency_code)))


def convert_money_to_major_units(money: Money) -> Decimal:
    """51700 GEL minor units -> Decimal("517.00")."""

    digits: int = int(get_currency_minor_unit_digits(money.currency_code))
    return Decimal(int(money.amount_minor)).scaleb(-digits)


def build_money_from_major_units(
    amount: Decimal,
    currency_code: CurrencyCode,
    rounding: str = ROUND_HALF_UP,
) -> Money:
    """
    Decimal("0.44328") GEL -> 44 minor units, rounded half up (or as asked).

    Raises:
        ValidationFailedError: the amount is negative or not finite.
    """

    if not amount.is_finite():
        raise ValidationFailedError("Money amount must be a finite number.")

    digits: int = int(get_currency_minor_unit_digits(currency_code))
    minor_units: Decimal = amount.scaleb(digits).quantize(
        WHOLE_MINOR_UNIT,
        rounding=rounding,
    )
    if minor_units < 0:
        raise ValidationFailedError("Money amount cannot be negative.")

    return Money(
        amount_minor=MoneyAmountMinor(int(minor_units)),
        currency_code=currency_code,
    )


def convert_money(
    money: Money,
    exchange_rate: ExchangeRateValue,
    target_currency_code: CurrencyCode,
) -> Money:
    """
    Convert with a rate in target units per source unit: 0.15 EUR x 2.9552 ->
    0.44 GEL. The rate is its exact decimal string, never a binary float;
    the result is rounded half to even.
    """

    return build_money_from_major_units(
        convert_money_to_major_units(money) * Decimal(str(exchange_rate)),
        target_currency_code,
        ROUND_HALF_EVEN,
    )


def multiply_money(money: Money, factor: Decimal) -> Money:
    """Scale an amount (12 months, a share of a package) in its own currency."""

    return build_money_from_major_units(
        convert_money_to_major_units(money) * factor,
        money.currency_code,
    )


def build_discount_factor(discount_percent: DiscountPercent) -> Decimal:
    """15 % -> Decimal("0.85")."""

    return (ONE_HUNDRED_PERCENT - Decimal(int(discount_percent))) / ONE_HUNDRED_PERCENT
