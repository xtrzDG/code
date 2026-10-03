"""A niche's typical check in a business's currency, rounded like a price people say."""

from decimal import ROUND_HALF_UP, Decimal

from app.schemas.dto.billing import Money
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import AverageCheckMinor
from app.utilities.money.money_math import (
    build_money_from_major_units,
    convert_money,
    convert_money_to_major_units,
)

SIGNIFICANT_DIGITS: int = 2


def typical_check_in(
    typical_check: Money | None,
    currency_code: CurrencyCode,
    rate: ExchangeRateQuote | None,
) -> AverageCheckMinor | None:
    """
    The typical check in `currency_code`: as it is in its own currency,
    else converted with the official `rate` (base: the check's currency)
    and rounded to two significant digits of whole units (40 € at 2.9552
    is 120 ₾, not 118.21 ₾); None without a check or a rate.
    """

    if typical_check is None:
        return None

    if typical_check.currency_code == currency_code:
        return AverageCheckMinor(int(typical_check.amount_minor))

    if rate is None or rate.quote_currency_code != currency_code:
        return None

    converted: Money = convert_money(typical_check, rate.rate_value, currency_code)
    major: Decimal = round_significant(convert_money_to_major_units(converted))
    return AverageCheckMinor(
        int(build_money_from_major_units(major, currency_code).amount_minor)
    )


def round_significant(amount: Decimal) -> Decimal:
    """`amount` to two significant digits of whole units (at least 1)."""

    whole: Decimal = amount.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    if whole < 1:
        return Decimal(1)

    exponent: int = max(0, whole.adjusted() + 1 - SIGNIFICANT_DIGITS)
    step: Decimal = Decimal(10) ** exponent
    return (whole / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step
