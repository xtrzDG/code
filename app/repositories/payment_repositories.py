from typed_time_provider import Microseconds

from app.contracts.billing import (
    PackageUsageWarningRepoContract,
    PaymentOrderRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.constants.billing import PackageMetric
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PaymentOrderRepository(
    BusinessScopedRepository[PaymentOrderDocument],
    PaymentOrderRepoContract,
):
    def save(self, payment_order: PaymentOrderDocument) -> None:
        self._store(str(payment_order.id), payment_order)

    def get(self, payment_order_id: PaymentOrderId) -> PaymentOrderDocument | None:
        return self._collection.get(str(payment_order_id))

    def list_by_business(self, business_id: BusinessId) -> list[PaymentOrderDocument]:
        return sorted(
            self._list(business_id),
            key=lambda payment_order: payment_order.created_at,
            reverse=True,
        )


class PackageUsageWarningRepository(
    BusinessScopedRepository[PackageUsageWarningDocument],
    PackageUsageWarningRepoContract,
):
    def save(self, warning: PackageUsageWarningDocument) -> None:
        self._store(str(warning.id), warning)

    def find(
        self,
        business_id: BusinessId,
        subscription_id: SubscriptionId,
        metric: PackageMetric,
        period_start: Microseconds,
    ) -> PackageUsageWarningDocument | None:
        for warning in self._list(business_id):
            if (
                warning.subscription_id == subscription_id
                and warning.metric is metric
                and warning.period_start == period_start
            ):
                return warning

        return None
