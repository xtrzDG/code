from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
    SpendLimitMarkRepoContract,
    UsageSpendRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals, of_business, time_range
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.business_limits import (
    BusinessLimitsDocument,
    SpendLimitMarkDocument,
)
from app.schemas.dto.spend_guard import UsageKindTotal
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantityTotal,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.schemas.typings.spend.prefixed_id import SpendLimitMarkId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.spend.spend_keys import business_limits_id_of

OCCURRED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("occurred_at")
KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
COST_FIELD: DocumentFieldPath = DocumentFieldPath("cost_micro_usd")
QUANTITY_FIELD: DocumentFieldPath = DocumentFieldPath("quantity")
DAY_FIELD: DocumentFieldPath = DocumentFieldPath("day")


class BusinessLimitsRepository(
    BusinessScopedRepository[BusinessLimitsDocument],
    BusinessLimitsRepoContract,
):
    """One limits document per business, keyed by the derived id."""

    def get_or_default(self, business_id: BusinessId) -> BusinessLimitsDocument:
        limits_id = business_limits_id_of(business_id)
        stored: BusinessLimitsDocument | None = self._load(business_id, str(limits_id))
        if stored is not None:
            return stored

        return BusinessLimitsDocument(id=limits_id, business_id=business_id)

    def save(self, limits: BusinessLimitsDocument) -> None:
        self._store(str(limits.id), limits)


class SpendLimitMarkRepository(
    BusinessScopedRepository[SpendLimitMarkDocument],
    SpendLimitMarkRepoContract,
):
    """The days a business passed a limit, each inserted once (derived ids)."""

    def get(
        self, business_id: BusinessId, mark_id: SpendLimitMarkId
    ) -> SpendLimitMarkDocument | None:
        return self._load(business_id, str(mark_id))

    def insert_if_absent(self, mark: SpendLimitMarkDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(mark.id), mark))

    def list_by_day(self, day: SpendDay) -> list[SpendLimitMarkDocument]:
        return self._collection.list_by_fields([field_equals(DAY_FIELD, day)])


class UsageSpendRepository(UsageSpendRepoContract):
    """
    Spend summed by the database: a business's usage over its
    (business_id, occurred_at) index (1010), the platform's over the
    occurred_at index that carries kind, cost and quantity (1142).
    """

    def __init__(
        self, collection: DocumentCollectionAdapterContract[UsageEventDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[UsageEventDocument] = (
            collection
        )

    def sum_business(
        self,
        business_id: BusinessId,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
    ) -> list[UsageKindTotal]:
        return self._sum(occurred_from, occurred_to, (of_business(business_id),))

    def sum_platform(
        self, occurred_from: Microseconds, occurred_to: Microseconds
    ) -> list[UsageKindTotal]:
        return self._sum(occurred_from, occurred_to, ())

    def _sum(
        self,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
        matches: tuple[DocumentFieldMatch, ...],
    ) -> list[UsageKindTotal]:
        groups: list[DocumentGroupCount] = self._collection.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=matches,
                    ranges=(time_range(OCCURRED_AT_FIELD, occurred_from, occurred_to),),
                ),
                group_by=(KIND_FIELD,),
                totals_of=(QUANTITY_FIELD, COST_FIELD),
            )
        )
        totals: list[UsageKindTotal] = []
        for group in groups:
            kind_value = group.values[0] if group.values else None
            if kind_value is None or str(kind_value) not in UsageKind:
                continue

            quantity, cost = (int(total) for total in group.totals)
            totals.append(
                UsageKindTotal(
                    kind=UsageKind(str(kind_value)),
                    quantity=UsageQuantityTotal(max(quantity, 0)),
                    cost_micro_usd=CostMicroUsd(max(cost, 0)),
                )
            )

        return totals
