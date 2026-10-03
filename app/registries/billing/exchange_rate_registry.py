import threading
from collections.abc import Sequence
from datetime import UTC, date, datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.repositories.exchange_rate_repositories import (
    ExchangeRateRepoContract,
)
from app.registries.billing.exchange_rate_catalog import FALLBACK_EXCHANGE_RATES
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.dto.billing_exchange_rates import PublishedExchangeRate
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.billing.constrained_strings import CurrencyPairCode
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.exchange_rates.rate_resolution import (
    newest_by_pair,
    pairs_to_read,
    resolve_rate,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
# Rates change once a day: a process asks the database again after this.
CACHE_MICROSECONDS: int = 10 * 60 * MICROSECONDS_PER_SECOND
type CacheKey = tuple[CurrencyCode, CurrencyCode]


class ExchangeRateRegistry(ExchangeRateRegistryContract):
    """
    The rates every money conversion uses (prices in local currencies,
    provider costs and margins, typical checks): the newest stored rate of
    each pair (the daily refresh of the NBG and ECB feeds), else the dated
    fallback catalog, resolved as published, inverse or cross rate through
    the euro (`resolve_rate`). One indexed read per pair of currencies,
    remembered for ten minutes per process.
    """

    def __init__(
        self,
        exchange_rate_repo: ExchangeRateRepoContract,
        wall_clock: WallClock[Microseconds],
        fallback_rates: Sequence[PublishedExchangeRate] = FALLBACK_EXCHANGE_RATES,
    ) -> None:
        self._exchange_rate_repo: ExchangeRateRepoContract = exchange_rate_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._fallback_rates: list[PublishedExchangeRate] = list(fallback_rates)
        self._cache: dict[CacheKey, tuple[int, ExchangeRateQuote | None]] = {}
        self._lock: threading.Lock = threading.Lock()

    def find_rate(
        self,
        base_currency_code: CurrencyCode,
        quote_currency_code: CurrencyCode,
    ) -> ExchangeRateQuote | None:
        now: int = int(self._wall_clock.now_unix())
        key: CacheKey = (base_currency_code, quote_currency_code)
        with self._lock:
            cached: tuple[int, ExchangeRateQuote | None] | None = self._cache.get(key)

        if cached is not None and now - cached[0] < CACHE_MICROSECONDS:
            return cached[1]

        pairs: list[CurrencyPairCode] = pairs_to_read(
            base_currency_code, quote_currency_code
        )
        stored: list[PublishedExchangeRate] = [
            published_from(document)
            for document in self._exchange_rate_repo.find_latest(pairs)
        ]
        quote: ExchangeRateQuote | None = resolve_rate(
            base_currency_code,
            quote_currency_code,
            newest_by_pair(stored, self._fallback_rates),
            today_of(now),
        )
        with self._lock:
            self._cache[key] = (now, quote)

        return quote


def published_from(document: ExchangeRateDocument) -> PublishedExchangeRate:
    return PublishedExchangeRate(
        base_currency_code=document.base_currency_code,
        quote_currency_code=document.quote_currency_code,
        rate=document.rate,
        rate_date=document.rate_date,
        source=document.source,
        is_derived=document.is_derived,
    )


def today_of(now: int) -> date:
    return datetime.fromtimestamp(now / MICROSECONDS_PER_SECOND, tz=UTC).date()
