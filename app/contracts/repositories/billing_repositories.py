"""
Persistence contracts of subscriptions, invoices and usage events.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.billing import (
    InvoiceDocument,
    OnboardingRequestDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId, SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class SubscriptionRepoContract(RepoContract, Protocol):
    def save(self, subscription: SubscriptionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        subscription_id: SubscriptionId,
    ) -> SubscriptionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[SubscriptionDocument]:
        raise NotImplementedError


class InvoiceRepoContract(RepoContract, Protocol):
    def save(self, invoice: InvoiceDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        invoice_id: InvoiceId,
    ) -> InvoiceDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[InvoiceDocument]:
        raise NotImplementedError


class UsageEventRepoContract(RepoContract, Protocol):
    def append(self, event: UsageEventDocument) -> None:
        raise NotImplementedError

    def list_by_business_between(
        self,
        business_id: BusinessId,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
    ) -> list[UsageEventDocument]:
        """Events with occurred_from <= occurred_at < occurred_to."""
        raise NotImplementedError


class OnboardingRequestRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> OnboardingRequestDocument | None:
        """The done-for-you setup request of a business, if it made one."""
        raise NotImplementedError

    def open_once(self, request: OnboardingRequestDocument) -> bool:
        """
        Store the request unless the business already has one (atomic, also
        across processes); True when it was stored now.
        """
        raise NotImplementedError

    def save(self, request: OnboardingRequestDocument) -> None:
        """Store a request's new state (the team marked it done)."""
        raise NotImplementedError
