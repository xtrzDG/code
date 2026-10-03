"""
Amounts of any currency in euro cents, with the official rates of the
exchange-rate registry (a direct pair, or the published opposite pair read
the other way); never with an invented rate.
"""

from decimal import Decimal

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.analytics.mrr_math import EUR, EuroConverter
from app.utilities.billing.client_cost_math import (
    MICRO_UNITS_PER_UNIT,
    PROVIDER_COST_CURRENCY,
    convert_amount,
    to_minor_units,
)
from app.utilities.money.money_math import get_currency_minor_unit_digits


def euro_converter(registry: ExchangeRateRegistryContract) -> EuroConverter:
    """Minor units of a currency -> euro cents; None without a rate."""

    def to_eur(amount_minor: int, currency_code: CurrencyCode) -> int | None:
        digits: int = int(get_currency_minor_unit_digits(currency_code))
        major: Decimal = Decimal(amount_minor).scaleb(-digits)
        converted = convert_amount(major, currency_code, EUR, registry)
        if converted is None:
            return None

        return to_minor_units(converted[0], EUR)

    return to_eur


def provider_cost_in_euros(
    cost_micro_usd: int, registry: ExchangeRateRegistryContract
) -> int | None:
    """Provider cost (micro US dollars) in euro cents; None without a rate."""

    if cost_micro_usd == 0:
        return 0

    converted = convert_amount(
        Decimal(cost_micro_usd) / MICRO_UNITS_PER_UNIT,
        PROVIDER_COST_CURRENCY,
        EUR,
        registry,
    )
    return None if converted is None else to_minor_units(converted[0], EUR)
