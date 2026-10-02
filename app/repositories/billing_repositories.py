from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import time_range
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId, SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

OCCURRED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("occurred_at")


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
            self._list_in_business(business_id),
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
            self._list_in_business(business_id),
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
        return self._list_in_range(
            business_id,
            time_range(
                OCCURRED_AT_FIELD,
                starting_at=occurred_from,
                ending_before=occurred_to,
            ),
        )
