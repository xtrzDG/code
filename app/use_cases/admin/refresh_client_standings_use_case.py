import logging
from itertools import batched

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_standing_repositories import (
    ClientStandingRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.client_health import AdminClientSort
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.dto.admin import AdminClientSummary, ClientSummarySource
from app.schemas.dto.client_standings import ClientListPositions
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_integers import (
    ClientListPosition,
)
from app.schemas.typings.client_health.strings import ClientSummarySnapshot
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.admin.client_list_order import (
    SORT_KEYS,
    SortKey,
    is_losing_money,
)
from app.use_cases.shared.business_walk import BUSINESS_BATCH_SIZE, walk_businesses

LOGGER: logging.Logger = logging.getLogger(__name__)
LIST_ORDERS: tuple[AdminClientSort, ...] = tuple(AdminClientSort)
# A client seen for the first time stands last until the ranking below
# places it, a moment later in the same run.
UNRANKED: ClientListPosition = ClientListPosition(10**12)

type OrderKeys = tuple[SortKey, ...]


class RefreshClientStandingsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The platform admin's client list, computed ahead (a periodic job of
    the worker, every 15 minutes).

    Walks every business in keyset batches, summarizes each client
    (`SummarizeClientUseCase`, the same summary as the client's page) and
    stores it with the fields the list filters by; then ranks every client
    in each order of the list (`client_list_order`) and stores the
    positions that changed. Only the order keys of every client stay in
    memory, never every summary. A client whose summary fails keeps its
    previous standing; the run goes on with the others.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        summarize_client: UseCaseContract[ClientSummarySource, AdminClientSummary],
        client_standing_repo: ClientStandingRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._summarize_client: UseCaseContract[
            ClientSummarySource, AdminClientSummary
        ] = summarize_client
        self._client_standing_repo: ClientStandingRepoContract = client_standing_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        keys: dict[BusinessId, OrderKeys] = {}
        stored: dict[BusinessId, ClientListPositions] = {}
        for batch in batched(
            walk_businesses(self._business_repo),
            int(BUSINESS_BATCH_SIZE),
            strict=False,
        ):
            self._refresh_batch(list(batch), keys, stored)

        for business_id, positions in rank(keys).items():
            if stored.get(business_id) != positions:
                self._client_standing_repo.move(business_id, positions)

        return JobReport(processed_count=ProcessedItemCount(len(keys)))

    def _refresh_batch(
        self,
        businesses: list[BusinessDocument],
        keys: dict[BusinessId, OrderKeys],
        stored: dict[BusinessId, ClientListPositions],
    ) -> None:
        previous: dict[BusinessId, ClientStandingDocument] = (
            self._client_standing_repo.get_many(
                [business.id for business in businesses]
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        standings: list[ClientStandingDocument] = []
        for business in businesses:
            earlier: ClientStandingDocument | None = previous.get(business.id)
            try:
                summary: AdminClientSummary = self._summarize_client.run(
                    ClientSummarySource(business=business)
                )
            except ApplicationError:
                # The previous standing stays as it was, positions too.
                LOGGER.warning(
                    "Client %s was not summarized; it keeps its standing.",
                    business.id,
                    exc_info=True,
                )
                continue

            keys[business.id] = tuple(
                SORT_KEYS[order](summary) for order in LIST_ORDERS
            )
            kept: ClientListPositions = (
                unranked() if earlier is None else positions_of(earlier)
            )
            stored[business.id] = kept
            standings.append(build_standing(summary, kept, earlier, now))

        self._client_standing_repo.save_many(standings)


def build_standing(
    summary: AdminClientSummary,
    positions: ClientListPositions,
    earlier: ClientStandingDocument | None,
    now: Microseconds,
) -> ClientStandingDocument:
    return ClientStandingDocument(
        business_id=summary.business_id,
        name=summary.name,
        business_status=summary.business_status,
        health_status=summary.health_status,
        country_code=summary.country_code,
        niche_key=summary.niche_key,
        is_losing_money=is_losing_money(summary),
        summary=ClientSummarySnapshot(summary.model_dump_json()),
        health_position=positions.health,
        name_position=positions.name,
        usage_position=positions.usage,
        margin_position=positions.margin,
        cost_position=positions.cost,
        revenue_position=positions.revenue,
        created_at=now if earlier is None else earlier.created_at,
        updated_at=now,
    )


def rank(keys: dict[BusinessId, OrderKeys]) -> dict[BusinessId, ClientListPositions]:
    """Every client's position in each order (0 first)."""

    places: dict[BusinessId, dict[AdminClientSort, int]] = {
        business_id: {} for business_id in keys
    }
    for index, order in enumerate(LIST_ORDERS):
        ordered: list[BusinessId] = sorted(
            keys, key=lambda business_id: keys[business_id][index]
        )
        for position, business_id in enumerate(ordered):
            places[business_id][order] = position

    return {
        business_id: ClientListPositions(
            health=ClientListPosition(place[AdminClientSort.HEALTH]),
            name=ClientListPosition(place[AdminClientSort.NAME]),
            usage=ClientListPosition(place[AdminClientSort.USAGE]),
            margin=ClientListPosition(place[AdminClientSort.MARGIN]),
            cost=ClientListPosition(place[AdminClientSort.COST]),
            revenue=ClientListPosition(place[AdminClientSort.REVENUE]),
        )
        for business_id, place in places.items()
    }


def positions_of(standing: ClientStandingDocument) -> ClientListPositions:
    return ClientListPositions(
        health=standing.health_position,
        name=standing.name_position,
        usage=standing.usage_position,
        margin=standing.margin_position,
        cost=standing.cost_position,
        revenue=standing.revenue_position,
    )


def unranked() -> ClientListPositions:
    return ClientListPositions(
        health=UNRANKED,
        name=UNRANKED,
        usage=UNRANKED,
        margin=UNRANKED,
        cost=UNRANKED,
        revenue=UNRANKED,
    )
