"""Exchange rate registries over in-memory dated rates, for the money tests."""

from collections.abc import Sequence
from datetime import UTC, datetime

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.billing.exchange_rate_catalog import FALLBACK_EXCHANGE_RATES
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.dto.billing_exchange_rates import PublishedExchangeRate
from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.exchange_rates.rate_derivation import build_rate_document

TODAY: str = "2026-10-03"
type StoredRate = tuple[str, str, str]


def day_clock(day: str = TODAY, hour: int = 12) -> WallClock[Microseconds]:
    moment: datetime = datetime.fromisoformat(f"{day}T{hour:02d}:00:00").replace(
        tzinfo=UTC
    )
    nanoseconds: int = int(moment.timestamp()) * 1_000_000_000
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: nanoseconds,
    )


def published(
    base: str,
    quote: str,
    rate: str,
    day: str = TODAY,
    source: ExchangeRateSource = ExchangeRateSource.ECB,
    is_derived: bool = False,
) -> PublishedExchangeRate:
    return PublishedExchangeRate(
        base_currency_code=CurrencyCode(base),
        quote_currency_code=CurrencyCode(quote),
        rate=ExchangeRateValue(rate),
        rate_date=ExchangeRateDate(day),
        source=source,
        is_derived=is_derived,
    )


def rate_repository(
    rates: Sequence[PublishedExchangeRate] = (),
) -> ExchangeRateRepository:
    repository = ExchangeRateRepository(
        InMemoryDocumentCollectionAdapter[ExchangeRateDocument](ExchangeRateDocument)
    )
    clock: WallClock[Microseconds] = day_clock()
    repository.save_many(
        [build_rate_document(rate, clock.now_unix()) for rate in rates]
    )
    return repository


def rate_registry(
    rates: Sequence[StoredRate] = (),
    today: str = TODAY,
    fallback: Sequence[PublishedExchangeRate] = FALLBACK_EXCHANGE_RATES,
) -> ExchangeRateRegistry:
    """A registry over stored rates (base, quote, rate) of `today` and the catalog."""

    return ExchangeRateRegistry(
        exchange_rate_repo=rate_repository(
            [published(base, quote, rate, today) for base, quote, rate in rates]
        ),
        wall_clock=day_clock(today),
        fallback_rates=fallback,
    )
