"""
Persistence contracts of the spend guard (migration 1142): each business's
limits, the marks of the days it passed one of them, and today's spend
summed by the database from the usage events.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.business_limits import (
    BusinessLimitsDocument,
    SpendLimitMarkDocument,
)
from app.schemas.dto.spend_guard import UsageKindTotal
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.schemas.typings.spend.prefixed_id import SpendLimitMarkId


class BusinessLimitsRepoContract(RepoContract, Protocol):
    def get_or_default(self, business_id: BusinessId) -> BusinessLimitsDocument:
        """The stored limits, or the defaults of a business without any."""
        raise NotImplementedError

    def save(self, limits: BusinessLimitsDocument) -> None:
        raise NotImplementedError


class SpendLimitMarkRepoContract(RepoContract, Protocol):
    def get(
        self, business_id: BusinessId, mark_id: SpendLimitMarkId
    ) -> SpendLimitMarkDocument | None:
        raise NotImplementedError

    def insert_if_absent(self, mark: SpendLimitMarkDocument) -> bool:
        """
        Store the mark unless one with its id exists (atomic, also across
        processes); True when it was stored now.
        """
        raise NotImplementedError

    def list_by_day(self, day: SpendDay) -> list[SpendLimitMarkDocument]:
        """Every business's marks of one day (indexed by day, 1142)."""
        raise NotImplementedError


class UsageSpendRepoContract(RepoContract, Protocol):
    def sum_business(
        self,
        business_id: BusinessId,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
    ) -> list[UsageKindTotal]:
        """One business's usage with occurred_from <= occurred_at < occurred_to."""
        raise NotImplementedError

    def sum_platform(
        self, occurred_from: Microseconds, occurred_to: Microseconds
    ) -> list[UsageKindTotal]:
        """Every business's usage of the window, summed by kind."""
        raise NotImplementedError
