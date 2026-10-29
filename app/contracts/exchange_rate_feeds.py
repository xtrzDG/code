"""The banks whose published exchange rates the platform reads."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.dto.billing_exchange_rates import ExchangeRateSheet


class ExchangeRateFeedClientContract(ClientContract, Protocol):
    """One central bank's rate feed, read over the SSRF-guarded fetcher."""

    def fetch_latest(self) -> ExchangeRateSheet:
        """
        The rates the bank published for its latest day.

        Raises:
            ExchangeRateFeedError: the feed could not be read or understood.
        """
        raise NotImplementedError
