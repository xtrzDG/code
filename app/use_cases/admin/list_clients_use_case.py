from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.client_health import AdminClientSort, ClientHealthStatus
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import (
    AdminClientPage,
    AdminClientsQuery,
    AdminClientSummary,
    AdminClientTotals,
    ClientSummarySource,
)
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.client_health.constrained_integers import ClientCount
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.paging.ordered_paging import take_ordered_page

HEALTH_ORDER: dict[ClientHealthStatus, int] = {
    ClientHealthStatus.CRITICAL: 0,
    ClientHealthStatus.ATTENTION: 1,
    ClientHealthStatus.HEALTHY: 2,
}

# Sort keys put unknown values last: (1, ...) after (0, value).
type SortKey = tuple[object, ...]


class ListClientsUseCase(UseCaseContract[AdminClientsQuery, AdminClientPage]):
    """
    Clients of the platform for the platform admin (concept /admin): status,
    plan, published version, last autotest, handoffs, open questions, usage
    and margin.

    Filters (business status, health, country, niche, part of the name or
    id) run before paging; the order is chosen by the admin (critical
    clients first by default, see AdminClientSort). The page also carries
    totals over every client and the countries and niches present, for the
    summary tiles and the filter choices.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        business_repo: BusinessRepoContract,
        summarize_client: UseCaseContract[ClientSummarySource, AdminClientSummary],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._summarize_client: UseCaseContract[
            ClientSummarySource,
            AdminClientSummary,
        ] = summarize_client
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminClientsQuery) -> AdminClientPage:
        self._authorize_platform_admin.run(input_data.user_id)
        summaries: list[AdminClientSummary] = [
            self._summarize_client.run(ClientSummarySource(business=business))
            for business in self._business_repo.list_all()
        ]
        matching: list[AdminClientSummary] = sorted(
            (summary for summary in summaries if matches_filters(summary, input_data)),
            key=SORT_KEYS[input_data.sort],
        )
        items, next_cursor = take_ordered_page(
            matching,
            input_data.page,
            item_id=lambda summary: str(summary.business_id),
        )
        return AdminClientPage(
            generated_at=self._wall_clock.now_unix(),
            items=items,
            next_cursor=next_cursor,
            matching_count=ClientCount(len(matching)),
            totals=count_totals(summaries),
            countries=sorted(
                {summary.country_code for summary in summaries},
                key=str,
            ),
            niches=sorted(
                {summary.niche_key for summary in summaries},
                key=lambda niche: niche.value,
            ),
        )


def matches_filters(summary: AdminClientSummary, query: AdminClientsQuery) -> bool:
    return (
        (query.status is None or summary.business_status is query.status)
        and (query.health is None or summary.health_status is query.health)
        and (query.country_code is None or summary.country_code == query.country_code)
        and (query.niche_key is None or summary.niche_key is query.niche_key)
        and matches_search(summary, query.search)
    )


def matches_search(
    summary: AdminClientSummary, search: ClientSearchText | None
) -> bool:
    if search is None:
        return True

    needle: str = str(search).strip().casefold()
    return needle in str(summary.name).casefold() or needle in (
        str(summary.business_id).casefold()
    )


def count_totals(summaries: list[AdminClientSummary]) -> AdminClientTotals:
    def count(condition: Callable[[AdminClientSummary], bool]) -> ClientCount:
        return ClientCount(sum(1 for summary in summaries if condition(summary)))

    return AdminClientTotals(
        client_count=ClientCount(len(summaries)),
        critical_count=count(
            lambda summary: summary.health_status is ClientHealthStatus.CRITICAL
        ),
        attention_count=count(
            lambda summary: summary.health_status is ClientHealthStatus.ATTENTION
        ),
        healthy_count=count(
            lambda summary: summary.health_status is ClientHealthStatus.HEALTHY
        ),
        losing_money_count=count(
            lambda summary: (
                summary.cost.margin is not None
                and int(summary.cost.margin.amount_minor) < 0
            )
        ),
    )


def find_usage_percent(summary: AdminClientSummary) -> float | None:
    """The fuller of the two packages (voice minutes, dialogs), or None."""

    percents: list[float] = [
        int(used) / int(included) * 100
        for used, included in (
            (summary.used_voice_minutes, summary.included_voice_minutes),
            (summary.used_dialogs, summary.included_dialogs),
        )
        if int(included) > 0
    ]
    return max(percents, default=None)


def health_key(summary: AdminClientSummary) -> SortKey:
    return (
        HEALTH_ORDER[summary.health_status],
        -len(summary.health_issues),
        *name_key(summary),
    )


def name_key(summary: AdminClientSummary) -> SortKey:
    return (str(summary.name).casefold(), str(summary.business_id))


def known_first(value: float | None) -> SortKey:
    """Unknown values sort after every known one."""

    return (1, 0.0) if value is None else (0, value)


def usage_key(summary: AdminClientSummary) -> SortKey:
    percent: float | None = find_usage_percent(summary)
    return (*known_first(None if percent is None else -percent), *health_key(summary))


def margin_key(summary: AdminClientSummary) -> SortKey:
    margin_percent: GrossMarginPercent | None = summary.cost.margin_percent
    return (
        *known_first(None if margin_percent is None else float(margin_percent)),
        *health_key(summary),
    )


def cost_key(summary: AdminClientSummary) -> SortKey:
    return (-int(summary.cost.provider_cost_micro_usd), *health_key(summary))


def revenue_key(summary: AdminClientSummary) -> SortKey:
    revenue: Money = summary.cost.revenue
    return (
        str(revenue.currency_code),
        -int(revenue.amount_minor),
        *health_key(summary),
    )


SORT_KEYS: dict[AdminClientSort, Callable[[AdminClientSummary], SortKey]] = {
    AdminClientSort.HEALTH: health_key,
    AdminClientSort.NAME: name_key,
    AdminClientSort.USAGE: usage_key,
    AdminClientSort.MARGIN: margin_key,
    AdminClientSort.COST: cost_key,
    AdminClientSort.REVENUE: revenue_key,
}
