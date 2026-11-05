"""
Which rate converts base -> quote, from the newest rate of each pair: the
published pair itself, else its inverse, else a cross rate through the euro
(the pivot every currency has a rate against). Inverses and cross rates are
marked derived; a rate is stale when its day is more than a few days old.
"""

from collections.abc import Mapping
from datetime import date
from typing import NamedTuple

from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.billing_exchange_rates import PublishedExchangeRate
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.billing.constrained_strings import (
    CurrencyPairCode,
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.billing.strings import ExchangeRateSourceName
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.exchange_rates.rate_math import (
    days_between,
    divide_rates,
    invert_rate,
    older_date,
    pair_code,
)

PIVOT_CURRENCY: CurrencyCode = CurrencyCode("EUR")
# Banks publish on working days: a rate older than this says the refresh
# has stopped, and the cabinet shows it with its date as stale.
STALE_AFTER_DAYS: int = 4
SOURCE_NAMES: Mapping[ExchangeRateSource, str] = {
    ExchangeRateSource.NBG: "National Bank of Georgia",
    ExchangeRateSource.ECB: "European Central Bank",
    ExchangeRateSource.PLANNING: "Platform planning rate",
}
type RatesByPair = Mapping[CurrencyPairCode, PublishedExchangeRate]


class RateLeg(NamedTuple):
    """A currency's rate against the pivot (EUR -> currency)."""

    rate: ExchangeRateValue
    rate_date: ExchangeRateDate | None
    sources: frozenset[ExchangeRateSource]
    is_derived: bool


def pairs_to_read(base: CurrencyCode, quote: CurrencyCode) -> list[CurrencyPairCode]:
    """Every pair `resolve_rate` may need for base -> quote."""

    pairs: list[CurrencyPairCode] = [pair_code(base, quote), pair_code(quote, base)]
    for currency in (base, quote):
        if currency != PIVOT_CURRENCY:
            pairs.append(pair_code(PIVOT_CURRENCY, currency))
            pairs.append(pair_code(currency, PIVOT_CURRENCY))

    return list(dict.fromkeys(pairs))


def resolve_rate(
    base: CurrencyCode,
    quote: CurrencyCode,
    rates: RatesByPair,
    today: date,
) -> ExchangeRateQuote | None:
    """The newest rate base -> quote: published, inverse or via the euro."""

    if base == quote:
        return None

    direct: PublishedExchangeRate | None = rates.get(pair_code(base, quote))
    if direct is not None:
        return build_quote(
            base,
            quote,
            RateLeg(
                direct.rate,
                direct.rate_date,
                frozenset({direct.source}),
                direct.is_derived,
            ),
            today,
        )

    opposite: PublishedExchangeRate | None = rates.get(pair_code(quote, base))
    inverse: ExchangeRateValue | None = (
        None if opposite is None else invert_rate(opposite.rate)
    )
    if opposite is not None and inverse is not None:
        leg = RateLeg(inverse, opposite.rate_date, frozenset({opposite.source}), True)
        return build_quote(base, quote, leg, today)

    return cross_through_pivot(base, quote, rates, today)


def cross_through_pivot(
    base: CurrencyCode,
    quote: CurrencyCode,
    rates: RatesByPair,
    today: date,
) -> ExchangeRateQuote | None:
    """base -> quote = (EUR -> quote) / (EUR -> base)."""

    to_base: RateLeg | None = leg_from_pivot(base, rates)
    to_quote: RateLeg | None = leg_from_pivot(quote, rates)
    if to_base is None or to_quote is None:
        return None

    rate: ExchangeRateValue | None = divide_rates(to_quote.rate, to_base.rate)
    if rate is None:
        return None

    dates: list[ExchangeRateDate] = [
        leg.rate_date for leg in (to_base, to_quote) if leg.rate_date is not None
    ]
    leg = RateLeg(
        rate,
        dates[0] if len(dates) == 1 else older_date(dates[0], dates[1]),
        to_base.sources | to_quote.sources,
        True,
    )
    return build_quote(base, quote, leg, today)


def leg_from_pivot(currency: CurrencyCode, rates: RatesByPair) -> RateLeg | None:
    """EUR -> currency: 1 for the euro, the published rate, or its inverse."""

    if currency == PIVOT_CURRENCY:
        return RateLeg(ExchangeRateValue("1"), None, frozenset(), False)

    published: PublishedExchangeRate | None = rates.get(
        pair_code(PIVOT_CURRENCY, currency)
    )
    if published is not None:
        return RateLeg(
            published.rate,
            published.rate_date,
            frozenset({published.source}),
            published.is_derived,
        )

    opposite: PublishedExchangeRate | None = rates.get(
        pair_code(currency, PIVOT_CURRENCY)
    )
    inverse: ExchangeRateValue | None = (
        None if opposite is None else invert_rate(opposite.rate)
    )
    if opposite is None or inverse is None:
        return None

    return RateLeg(inverse, opposite.rate_date, frozenset({opposite.source}), True)


def build_quote(
    base: CurrencyCode,
    quote: CurrencyCode,
    leg: RateLeg,
    today: date,
) -> ExchangeRateQuote | None:
    if leg.rate_date is None:
        return None

    return ExchangeRateQuote(
        base_currency_code=base,
        quote_currency_code=quote,
        rate_value=leg.rate,
        rate_date=leg.rate_date,
        source=ExchangeRateSourceName(
            ", ".join(sorted(SOURCE_NAMES[source] for source in leg.sources))
        ),
        sources=sorted(leg.sources),
        is_derived=leg.is_derived,
        is_stale=days_between(leg.rate_date, today) > STALE_AFTER_DAYS,
    )


def newest_by_pair(
    *groups: list[PublishedExchangeRate],
) -> dict[CurrencyPairCode, PublishedExchangeRate]:
    """The newest rate of each pair over every group (ties: the earlier group)."""

    newest: dict[CurrencyPairCode, PublishedExchangeRate] = {}
    for group in groups:
        for rate in group:
            pair: CurrencyPairCode = pair_code(
                rate.base_currency_code, rate.quote_currency_code
            )
            known: PublishedExchangeRate | None = newest.get(pair)
            if known is None or str(rate.rate_date) > str(known.rate_date):
                newest[pair] = rate

    return newest
