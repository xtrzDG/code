from typed_time_provider import Microseconds

from app.contracts.repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId, SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class SubscriptionRepository(
    BusinessScopedRepository[SubscriptionDocument],
    SubscriptionRepoContract,
):
    def save(self, subscription: SubscriptionDocument) -> None:
        self._store(str(subscription.id), subscription)

    def get(
        self,
        business_id: BusinessId,
        subscription_id: SubscriptionId,
    ) -> SubscriptionDocument | None:
        return self._load(business_id, str(subscription_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[SubscriptionDocument]:
        return sorted(
            self._list(business_id),
            key=lambda subscription: subscription.period_start,
        )


class InvoiceRepository(
    BusinessScopedRepository[InvoiceDocument],
    InvoiceRepoContract,
):
    def save(self, invoice: InvoiceDocument) -> None:
        self._store(str(invoice.id), invoice)

    def get(
        self,
        business_id: BusinessId,
        invoice_id: InvoiceId,
    ) -> InvoiceDocument | None:
        return self._load(business_id, str(invoice_id))

    def list_by_business(self, business_id: BusinessId) -> list[InvoiceDocument]:
        return sorted(
            self._list(business_id),
            key=lambda invoice: invoice.period_start,
            reverse=True,
        )


class UsageEventRepository(
    BusinessScopedRepository[UsageEventDocument],
    UsageEventRepoContract,
):
    def append(self, event: UsageEventDocument) -> None:
        self._store(str(event.id), event)

    def list_by_business_between(
        self,
        business_id: BusinessId,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
    ) -> list[UsageEventDocument]:
        events: list[UsageEventDocument] = [
            event
            for event in self._list(business_id)
            if occurred_from <= event.occurred_at < occurred_to
        ]
        return sorted(events, key=lambda event: event.occurred_at)
