"""The platform admin's client list, stored ranked (migration 1122)."""

from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.client_standing_repositories import (
    ClientStandingRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.document_queries import document_position, field_equals
from app.schemas.constants.client_health import AdminClientSort, ClientHealthStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.dto.admin import AdminClientTotals
from app.schemas.dto.client_standings import (
    ClientChoices,
    ClientListPositions,
    ClientStandingFilter,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_integers import ClientCount
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

BUSINESS_STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("business_status")
HEALTH_STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("health_status")
COUNTRY_CODE_FIELD: DocumentFieldPath = DocumentFieldPath("country_code")
NICHE_KEY_FIELD: DocumentFieldPath = DocumentFieldPath("niche_key")
IS_LOSING_MONEY_FIELD: DocumentFieldPath = DocumentFieldPath("is_losing_money")
POSITION_FIELDS: dict[AdminClientSort, DocumentFieldPath] = {
    AdminClientSort.HEALTH: DocumentFieldPath("health_position"),
    AdminClientSort.NAME: DocumentFieldPath("name_position"),
    AdminClientSort.USAGE: DocumentFieldPath("usage_position"),
    AdminClientSort.MARGIN: DocumentFieldPath("margin_position"),
    AdminClientSort.COST: DocumentFieldPath("cost_position"),
    AdminClientSort.REVENUE: DocumentFieldPath("revenue_position"),
}


class ClientStandingRepository(ClientStandingRepoContract):
    """
    Standings stored under their business id; pages by one position column
    each order, counts grouped by the filter columns (all indexed).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ClientStandingDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[ClientStandingDocument] = (
            collection
        )

    def get_many(
        self, business_ids: Sequence[BusinessId]
    ) -> dict[BusinessId, ClientStandingDocument]:
        return {
            standing.business_id: standing
            for standing in self._collection.get_many(
                [str(business_id) for business_id in business_ids]
            )
        }

    def save_many(self, standings: Sequence[ClientStandingDocument]) -> None:
        self._collection.upsert_many(
            [(str(standing.business_id), standing) for standing in standings]
        )

    def move(self, business_id: BusinessId, positions: ClientListPositions) -> None:
        def place(stored: ClientStandingDocument) -> ClientStandingDocument:
            return stored.model_copy(
                update={
                    "health_position": positions.health,
                    "name_position": positions.name,
                    "usage_position": positions.usage,
                    "margin_position": positions.margin,
                    "cost_position": positions.cost,
                    "revenue_position": positions.revenue,
                }
            )

        self._collection.modify(str(business_id), place)

    def page(
        self,
        sort: AdminClientSort,
        where: ClientStandingFilter,
        window: KeysetSlice,
    ) -> list[ClientStandingDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                where=standing_filter(where),
                sort_fields=(POSITION_FIELDS[sort],),
                is_descending=False,
                after=document_position(window.after),
                limit=DocumentQueryLimit(int(window.limit)),
            )
        )

    def count(self, where: ClientStandingFilter) -> ClientCount:
        groups: list[DocumentGroupCount] = self._collection.count_by(
            DocumentAggregation(where=standing_filter(where))
        )
        return ClientCount(sum(int(group.count) for group in groups))

    def tally(self) -> AdminClientTotals:
        counts: dict[ClientHealthStatus, int] = dict.fromkeys(ClientHealthStatus, 0)
        losing_money: int = 0
        for group in self._collection.count_by(
            DocumentAggregation(group_by=(HEALTH_STATUS_FIELD, IS_LOSING_MONEY_FIELD))
        ):
            health: ClientHealthStatus | None = parse_choice(
                ClientHealthStatus, group.values[0]
            )
            if health is not None:
                counts[health] += int(group.count)
            if str(group.values[1]) == "true":
                losing_money += int(group.count)

        return AdminClientTotals(
            client_count=ClientCount(sum(counts.values())),
            critical_count=ClientCount(counts[ClientHealthStatus.CRITICAL]),
            attention_count=ClientCount(counts[ClientHealthStatus.ATTENTION]),
            healthy_count=ClientCount(counts[ClientHealthStatus.HEALTHY]),
            losing_money_count=ClientCount(losing_money),
        )

    def list_choices(self) -> ClientChoices:
        countries: set[CountryCode] = set()
        niches: set[NicheKey] = set()
        for group in self._collection.count_by(
            DocumentAggregation(group_by=(COUNTRY_CODE_FIELD, NICHE_KEY_FIELD))
        ):
            if group.values[0] is not None:
                countries.add(CountryCode(str(group.values[0])))
            niche: NicheKey | None = parse_choice(NicheKey, group.values[1])
            if niche is not None:
                niches.add(niche)

        return ClientChoices(
            countries=sorted(countries, key=str),
            niches=sorted(niches, key=lambda niche: niche.value),
        )


def standing_filter(where: ClientStandingFilter) -> DocumentFilter:
    """The filter's set fields as indexed matches."""

    matches: list[DocumentFieldMatch] = [
        field_equals(field, value)
        for field, value in (
            (BUSINESS_STATUS_FIELD, where.business_status),
            (HEALTH_STATUS_FIELD, where.health_status),
            (COUNTRY_CODE_FIELD, where.country_code),
            (NICHE_KEY_FIELD, where.niche_key),
        )
        if value is not None
    ]
    return DocumentFilter(matches=tuple(matches))
