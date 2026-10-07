"""Exchange rates as feeds publish them and as the registry reasons about them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.typings.billing.booleans import IsDerivedExchangeRate
from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class PublishedExchangeRate(ImmutableDTO):
    """
    A rate of one day: `rate` units of the quote currency per base unit,
    who set it, and whether it was derived from two published rates.
    """

    base_currency_code: CurrencyCode
    quote_currency_code: CurrencyCode
    rate: ExchangeRateValue
    rate_date: ExchangeRateDate
    source: ExchangeRateSource
    is_derived: IsDerivedExchangeRate = False


class ExchangeRateSheet(ImmutableDTO):
    """
    The rates one feed published for one day: the NBG's lari rates (base:
    each currency, quote: GEL) or the ECB's euro reference rates (base:
    EUR, quote: each currency).
    """

    source: ExchangeRateSource
    rate_date: ExchangeRateDate
    rates: list[PublishedExchangeRate] = Field(
        default_factory=list[PublishedExchangeRate]
    )
