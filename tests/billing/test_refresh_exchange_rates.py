"""The daily refresh: NBG and ECB sheets as dated rows, plus derived euro rates."""

import logging

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.schemas.constants.billing import ExchangeRateSource
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.exceptions.exchange_rate_errors import ExchangeRateFeedError
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.billing.refresh_exchange_rates_use_case import (
    RefreshExchangeRatesUseCase,
)
from tests.billing.exchange_rate_fixtures import day_clock
from tests.billing.rate_feed_fakes import (
    FixtureFetcher,
    fixture_fetcher,
    fixture_rate_clients,
)


class RefreshWorld:
    """The refresh job over fixture feeds and an in-memory rate collection."""

    def __init__(self, fetcher: FixtureFetcher | None = None) -> None:
        self.collection = InMemoryDocumentCollectionAdapter[ExchangeRateDocument](
            ExchangeRateDocument
        )
        self.repository = ExchangeRateRepository(self.collection)
        lari, euro = fixture_rate_clients(fetcher)
        self.refresh = RefreshExchangeRatesUseCase(
            lari_feed=lari,
            euro_feed=euro,
            exchange_rate_repo=self.repository,
            wall_clock=day_clock("2026-10-03", hour=6),
        )
        self.registry = ExchangeRateRegistry(
            exchange_rate_repo=self.repository,
            wall_clock=day_clock("2026-10-03"),
            fallback_rates=(),
        )

    def run(self) -> int:
        tick = JobTick(
            job_name=JobName("refresh_exchange_rates"),
            scheduled_at=day_clock("2026-10-03", hour=6).now_unix(),
        )
        return int(self.refresh.run(tick).processed_count)

    def stored(self) -> dict[str, tuple[str, str, bool]]:
        return {
            f"{row.source}:{row.pair}": (
                str(row.rate),
                str(row.rate_date),
                row.is_derived,
            )
            for row in self.collection.list_all()
        }

    def rate(self, base: str, quote: str) -> str:
        found = self.registry.find_rate(CurrencyCode(base), CurrencyCode(quote))
        assert found is not None
        return str(found.rate_value)


def test_both_feeds_are_stored_with_euro_rates_derived_through_the_lari() -> None:
    world = RefreshWorld()

    # 9 NBG + 8 ECB rates, and EUR -> AMD, AZN, KZT, UAH that only the NBG has.
    assert world.run() == 21
    stored = world.stored()
    assert stored["nbg:USD/GEL"] == ("2.6045", "2026-10-03", False)
    assert stored["ecb:EUR/USD"] == ("1.1351", "2026-10-02", False)
    assert stored["nbg:EUR/AMD"] == ("429.445090063916", "2026-10-03", True)
    assert stored["nbg:EUR/AZN"] == ("1.929573787612", "2026-10-03", True)
    # The ECB's own euro rates are not derived again from the lari.
    assert "nbg:EUR/USD" not in stored and "nbg:EUR/JPY" not in stored


def test_after_a_refresh_every_currency_converts_to_every_other() -> None:
    world = RefreshWorld()
    world.run()

    assert world.rate("USD", "GEL") == "2.6045"
    assert world.rate("JPY", "GEL") == "0.017584"
    assert world.rate("EUR", "INR") == "96.441"
    assert world.rate("USD", "AMD") == "378.33238486822"
    usd_in_amd = world.registry.find_rate(CurrencyCode("USD"), CurrencyCode("AMD"))
    assert usd_in_amd is not None
    assert usd_in_amd.is_derived is True
    assert str(usd_in_amd.rate_date) == "2026-10-02"


def test_running_again_on_the_same_day_replaces_the_rows() -> None:
    world = RefreshWorld()

    world.run()
    world.run()

    assert len(world.collection.list_all()) == 21


def test_a_feed_that_fails_is_skipped_and_the_other_is_stored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    without_ecb = RefreshWorld(fixture_fetcher(ecb=None))
    without_nbg = RefreshWorld(fixture_fetcher(nbg=None))

    with caplog.at_level(logging.WARNING):
        # Without the ECB, the NBG's lari sheet gives every euro rate.
        assert without_ecb.run() == 9 + 8
        assert without_nbg.run() == 8

    assert without_ecb.stored()["nbg:EUR/USD"][2] is True
    assert {row.source for row in without_nbg.collection.list_all()} == {
        ExchangeRateSource.ECB
    }
    assert caplog.text.count("Exchange rate feed skipped") == 2


def test_when_no_feed_can_be_read_the_job_fails_and_stores_nothing() -> None:
    world = RefreshWorld(fixture_fetcher(nbg=None, ecb=None))

    with pytest.raises(ExchangeRateFeedError):
        world.run()

    assert world.collection.list_all() == []
