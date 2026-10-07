"""
Which dated rate converts what: published, inverse, cross through the euro,
the fallback catalog, staleness and the per-process cache.
"""

from typed_time_provider import Microseconds, WallClock

from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.exchange_rates.rate_derivation import build_rate_document
from tests.billing.exchange_rate_fixtures import (
    day_clock,
    published,
    rate_registry,
    rate_repository,
)

SECONDS: int = 1_000_000_000


def find(
    registry: ExchangeRateRegistry, base: str, quote: str
) -> ExchangeRateQuote | None:
    return registry.find_rate(CurrencyCode(base), CurrencyCode(quote))


def described(quote: ExchangeRateQuote | None) -> tuple[str, str, str, bool, bool]:
    assert quote is not None
    return (
        str(quote.rate_value),
        str(quote.rate_date),
        str(quote.source),
        quote.is_derived,
        quote.is_stale,
    )


def test_a_published_pair_is_used_as_it_is() -> None:
    registry = rate_registry([("EUR", "USD", "1.1351")], fallback=())

    quote = find(registry, "EUR", "USD")

    assert described(quote) == (
        "1.1351",
        "2026-10-03",
        "European Central Bank",
        False,
        False,
    )
    assert quote is not None and quote.rate == 1.1351


def test_the_opposite_pair_is_inverted_and_marked_derived() -> None:
    registry = rate_registry([("USD", "GEL", "2.6045")], fallback=())

    assert described(find(registry, "GEL", "USD")) == (
        "0.383950854291",
        "2026-10-03",
        "European Central Bank",
        True,
        False,
    )


def test_other_pairs_cross_through_the_euro_as_old_as_their_older_leg() -> None:
    registry = ExchangeRateRegistry(
        exchange_rate_repo=rate_repository(
            [
                published("EUR", "USD", "1.1351", "2026-10-02"),
                published(
                    "EUR",
                    "AMD",
                    "429.445090063916",
                    "2026-10-03",
                    ExchangeRateSource.NBG,
                    is_derived=True,
                ),
            ]
        ),
        wall_clock=day_clock(),
        fallback_rates=(),
    )

    quote = find(registry, "USD", "AMD")
    assert described(quote) == (
        "378.33238486822",
        "2026-10-02",
        "European Central Bank, National Bank of Georgia",
        True,
        False,
    )
    assert quote is not None
    assert quote.sources == [ExchangeRateSource.ECB, ExchangeRateSource.NBG]


def test_no_rate_without_both_legs_or_for_the_same_currency() -> None:
    registry = rate_registry([("EUR", "USD", "1.1351")], fallback=())

    assert find(registry, "USD", "JPY") is None
    assert find(registry, "EUR", "EUR") is None


def test_before_the_first_refresh_the_dated_catalog_answers() -> None:
    registry = rate_registry()

    assert described(find(registry, "EUR", "GEL")) == (
        "2.9552",
        "2026-09-30",
        "National Bank of Georgia",
        False,
        False,
    )
    # Dollar provider costs reach lari through the euro.
    usd_in_lari = find(registry, "USD", "GEL")
    assert usd_in_lari is not None
    assert str(usd_in_lari.rate_value) == "2.604159323229"
    assert usd_in_lari.is_derived is True


def test_a_stored_rate_wins_over_the_catalog_and_an_old_one_is_stale() -> None:
    fresh = rate_registry([("EUR", "GEL", "2.9563")])
    old = rate_registry(today="2026-10-12")

    assert described(find(fresh, "EUR", "GEL"))[0] == "2.9563"
    assert described(find(old, "EUR", "GEL")) == (
        "2.9552",
        "2026-09-30",
        "National Bank of Georgia",
        False,
        True,
    )


def test_the_newest_day_of_a_pair_wins() -> None:
    registry = ExchangeRateRegistry(
        exchange_rate_repo=rate_repository(
            [
                published("EUR", "USD", "1.1300", "2026-09-29"),
                published("EUR", "USD", "1.1351", "2026-10-02"),
                published("EUR", "USD", "1.1200", "2026-09-30"),
            ]
        ),
        wall_clock=day_clock(),
        fallback_rates=(),
    )

    assert described(find(registry, "EUR", "USD"))[:2] == ("1.1351", "2026-10-02")


def test_a_process_asks_the_database_again_after_ten_minutes() -> None:
    now: list[int] = [1_790_000_000 * SECONDS]
    clock = WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: now[0],
    )
    repository = rate_repository([published("EUR", "USD", "1.1351", "2026-09-20")])
    registry = ExchangeRateRegistry(
        exchange_rate_repo=repository, wall_clock=clock, fallback_rates=()
    )
    assert described(find(registry, "EUR", "USD"))[0] == "1.1351"

    newer = published("EUR", "USD", "1.1400", "2026-09-21")
    repository.save_many([build_rate_document(newer, clock.now_unix())])
    now[0] += 9 * 60 * SECONDS
    assert described(find(registry, "EUR", "USD"))[0] == "1.1351"

    now[0] += 2 * 60 * SECONDS
    assert described(find(registry, "EUR", "USD"))[0] == "1.1400"
