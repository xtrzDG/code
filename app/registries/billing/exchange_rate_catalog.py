"""
Rates the platform falls back to before (or while not) the daily refresh
has stored published ones (`refresh_exchange_rates`). Each has a named
source and a date, and is shown as stale once it is old; a stored rate of
the same pair that is as new or newer always wins.
"""

from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.billing_exchange_rates import PublishedExchangeRate
from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode

FALLBACK_EXCHANGE_RATES: tuple[PublishedExchangeRate, ...] = (
    # Concept: "1 € = 2,9552 ₾", official NBG rate on 30.09.2026.
    PublishedExchangeRate(
        base_currency_code=CurrencyCode("EUR"),
        quote_currency_code=CurrencyCode("GEL"),
        rate=ExchangeRateValue("2.9552"),
        rate_date=ExchangeRateDate("2026-09-30"),
        source=ExchangeRateSource.NBG,
    ),
    # The concept's cost model prices dollar costs in euros at $8 = 7.05 €
    # (01.10.2026): its planning rate, until the ECB's is stored.
    PublishedExchangeRate(
        base_currency_code=CurrencyCode("EUR"),
        quote_currency_code=CurrencyCode("USD"),
        rate=ExchangeRateValue("1.1348"),
        rate_date=ExchangeRateDate("2026-10-01"),
        source=ExchangeRateSource.PLANNING,
    ),
)
