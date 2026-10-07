"""
Persistence contract of the dated exchange rates (platform-wide: rates
belong to no business). Implementations return independent copies.
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.typings.billing.constrained_strings import CurrencyPairCode
from app.schemas.typings.storage.constrained_integers import DocumentCount


class ExchangeRateRepoContract(RepoContract, Protocol):
    def save_many(self, rates: Sequence[ExchangeRateDocument]) -> DocumentCount:
        """
        Store the rates of a day; a rate already stored for the same source,
        pair and day is replaced (a refresh may run several times a day).
        """
        raise NotImplementedError

    def find_latest(
        self,
        pairs: Sequence[CurrencyPairCode],
    ) -> list[ExchangeRateDocument]:
        """The newest stored rate of each pair that has one (indexed)."""
        raise NotImplementedError
