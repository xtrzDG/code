"""
Euro rates of the currencies only the NBG publishes (AMD, AZN, UAH, KZT...),
so every currency has a rate against the pivot the registry crosses through.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.dto.billing_exchange_rates import (
    ExchangeRateSheet,
    PublishedExchangeRate,
)
from app.schemas.typings.billing.constrained_strings import ExchangeRateValue
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.exchange_rates.rate_math import (
    divide_rates,
    pair_code,
    rate_day_number,
)
from app.utilities.exchange_rates.rate_resolution import PIVOT_CURRENCY


def derive_euro_rates(
    lari_sheet: ExchangeRateSheet,
    euro_published: frozenset[CurrencyCode],
) -> list[PublishedExchangeRate]:
    """
    EUR -> X = (EUR -> GEL) / (X -> GEL) for each currency of the NBG's
    lari sheet the ECB does not publish (`euro_published`), marked derived.
    """

    euro_in_lari: PublishedExchangeRate | None = next(
        (
            rate
            for rate in lari_sheet.rates
            if rate.base_currency_code == PIVOT_CURRENCY
        ),
        None,
    )
    if euro_in_lari is None:
        return []

    derived: list[PublishedExchangeRate] = []
    for rate in lari_sheet.rates:
        currency: CurrencyCode = rate.base_currency_code
        if currency == PIVOT_CURRENCY or currency in euro_published:
            continue

        euro_rate: ExchangeRateValue | None = divide_rates(euro_in_lari.rate, rate.rate)
        if euro_rate is not None:
            derived.append(
                PublishedExchangeRate(
                    base_currency_code=PIVOT_CURRENCY,
                    quote_currency_code=currency,
                    rate=euro_rate,
                    rate_date=lari_sheet.rate_date,
                    source=ExchangeRateSource.NBG,
                    is_derived=True,
                )
            )

    return derived


def build_rate_document(
    rate: PublishedExchangeRate, fetched_at: Microseconds
) -> ExchangeRateDocument:
    return ExchangeRateDocument(
        base_currency_code=rate.base_currency_code,
        quote_currency_code=rate.quote_currency_code,
        pair=pair_code(rate.base_currency_code, rate.quote_currency_code),
        rate=rate.rate,
        rate_date=rate.rate_date,
        rate_day=rate_day_number(rate.rate_date),
        source=rate.source,
        is_derived=rate.is_derived,
        fetched_at=fetched_at,
        created_at=fetched_at,
        updated_at=fetched_at,
    )
