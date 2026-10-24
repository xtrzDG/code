"""
What an owner pays a month for a rented number: the carrier's price with
the platform's markup, in the owner's currency, rounded up to a whole unit.
"""

from decimal import ROUND_CEILING, Decimal

from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.billing.constrained_strings import ExchangeRateValue
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.telephony.constrained_integers import (
    PhoneNumberPriceMarkupPercent,
    PhoneNumberRentalMinor,
)
from app.utilities.money.money_math import build_money_from_major_units

CARRIER_CURRENCY: CurrencyCode = CurrencyCode("USD")
MICRO_UNITS: Decimal = Decimal(1_000_000)
ONE_HUNDRED: Decimal = Decimal(100)


def price_rental(
    monthly_cost: CostMicroUsd,
    markup_percent: PhoneNumberPriceMarkupPercent,
    currency_code: CurrencyCode,
    usd_rate: ExchangeRateValue | None,
) -> Money:
    """
    $1.15 with 30 % in GEL at 2.7 a dollar: 4.04 GEL, rounded up to 5.00.
    Without a rate the price stays in dollars (`usd_rate` is units of the
    currency for one dollar; None for dollars themselves or no rate).
    """

    dollars: Decimal = (
        Decimal(int(monthly_cost))
        / MICRO_UNITS
        * (ONE_HUNDRED + Decimal(int(markup_percent)))
        / ONE_HUNDRED
    )
    if usd_rate is None or currency_code == CARRIER_CURRENCY:
        return whole_units(dollars, CARRIER_CURRENCY)

    return whole_units(dollars * Decimal(str(usd_rate)), currency_code)


def whole_units(amount: Decimal, currency_code: CurrencyCode) -> Money:
    """An amount rounded up to a whole unit of its currency (at least 1)."""

    return build_money_from_major_units(
        max(amount.to_integral_value(rounding=ROUND_CEILING), Decimal(1)),
        currency_code,
    )


def as_rental_minor(price: Money) -> PhoneNumberRentalMinor:
    """A quoted monthly price as the rental's stored price."""

    return PhoneNumberRentalMinor(int(price.amount_minor))
