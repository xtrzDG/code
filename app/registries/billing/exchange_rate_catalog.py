"""
Official exchange rates the platform may quote estimated prices with.

Only rates with a named source and date belong here; no rate is invented
for other currencies, so their local prices stay unknown until a rate or a
price-book entry is added.
"""

from app.schemas.dto.catalog import ExchangeRateQuote
from app.schemas.typings.billing.constrained_floats import ExchangeRate
from app.schemas.typings.billing.constrained_strings import ExchangeRateDate
from app.schemas.typings.billing.strings import ExchangeRateSourceName
from app.schemas.typings.localization.constrained_strings import CurrencyCode

OFFICIAL_EXCHANGE_RATES: tuple[ExchangeRateQuote, ...] = (
    # Concept: "1 € = 2,9552 ₾", official NBG rate on 30.09.2026.
    ExchangeRateQuote(
        base_currency_code=CurrencyCode("EUR"),
        quote_currency_code=CurrencyCode("GEL"),
        rate=ExchangeRate(2.9552),
        rate_date=ExchangeRateDate("2026-09-30"),
        source=ExchangeRateSourceName("National Bank of Georgia"),
    ),
)
