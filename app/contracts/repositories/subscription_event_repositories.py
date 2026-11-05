"""
Persistence contract of the subscription lifecycle (migration 1161): the
steps of a subscription's life, per business and by kind across
businesses.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.prefixed_id import (
    SubscriptionEventId,
)


class SubscriptionEventRepoContract(RepoContract, Protocol):
    def record(self, event: SubscriptionEventDocument) -> bool:
        """
        Store a step unless one with its id exists (atomic, also across
        processes): a win-back stage is recorded once. True when stored.
        """
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, event_id: SubscriptionEventId
    ) -> SubscriptionEventDocument | None:
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[SubscriptionEventDocument]:
        """Every step of the business (a few a year), oldest first."""
        raise NotImplementedError

    def list_of_kind(
        self,
        kind: SubscriptionEventKind,
        occurred_from: Microseconds,
        occurred_before: Microseconds,
    ) -> list[SubscriptionEventDocument]:
        """Steps of one kind in the window, across businesses, oldest first."""
        raise NotImplementedError
