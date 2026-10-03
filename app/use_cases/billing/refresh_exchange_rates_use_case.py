import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.exchange_rate_feeds import ExchangeRateFeedClientContract
from app.contracts.repositories.exchange_rate_repositories import (
    ExchangeRateRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.dto.billing_exchange_rates import (
    ExchangeRateSheet,
    PublishedExchangeRate,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.exchange_rate_errors import ExchangeRateFeedError
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.utilities.exchange_rates.rate_derivation import (
    build_rate_document,
    derive_euro_rates,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class RefreshExchangeRatesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job: store the day's published rates of the National Bank of
    Georgia (X -> GEL) and the European Central Bank (EUR -> X) as dated
    rows, plus the euro rates of the currencies only the NBG publishes
    (derived through the lari), so every money conversion of the platform
    reads one dated source (`ExchangeRateRegistry`). A feed that cannot be
    read is logged and skipped; the rates already stored stay current until
    they turn stale. Running it again the same day replaces the day's rows.
    Rates are public data: nothing is audited.
    """

    def __init__(
        self,
        lari_feed: ExchangeRateFeedClientContract,
        euro_feed: ExchangeRateFeedClientContract,
        exchange_rate_repo: ExchangeRateRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._lari_feed: ExchangeRateFeedClientContract = lari_feed
        self._euro_feed: ExchangeRateFeedClientContract = euro_feed
        self._exchange_rate_repo: ExchangeRateRepoContract = exchange_rate_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        lari_sheet: ExchangeRateSheet | None = read_sheet(self._lari_feed)
        euro_sheet: ExchangeRateSheet | None = read_sheet(self._euro_feed)
        if lari_sheet is None and euro_sheet is None:
            raise ExchangeRateFeedError("No exchange rate feed could be read.")

        rates: list[PublishedExchangeRate] = [
            rate for sheet in (lari_sheet, euro_sheet) if sheet for rate in sheet.rates
        ]
        if lari_sheet is not None:
            euro_published: frozenset[CurrencyCode] = frozenset(
                ()
                if euro_sheet is None
                else (rate.quote_currency_code for rate in euro_sheet.rates)
            )
            rates.extend(derive_euro_rates(lari_sheet, euro_published))

        now: Microseconds = self._wall_clock.now_unix()
        documents: list[ExchangeRateDocument] = [
            build_rate_document(rate, now) for rate in rates
        ]
        saved: DocumentCount = self._exchange_rate_repo.save_many(documents)
        LOGGER.info("Stored %d exchange rates", int(saved))
        return JobReport(processed_count=ProcessedItemCount(int(saved)))


def read_sheet(feed: ExchangeRateFeedClientContract) -> ExchangeRateSheet | None:
    try:
        return feed.fetch_latest()
    except ExchangeRateFeedError as error:
        LOGGER.warning("Exchange rate feed skipped: %s", error)
        return None
