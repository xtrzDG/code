"""The admin client list: health order, totals, filters, sorting and paging."""

import pytest

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import PlanKey, SubscriptionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.client_health import (
    AdminClientSort,
    ClientHealthIssue,
    ClientHealthStatus,
)
from app.schemas.dto.admin import (
    AdminClientsQuery,
    AdminClientSummary,
    ClientSummarySource,
)
from app.schemas.dto.billing import Money
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
)
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from tests.billing.admin_world import AdminWorld, build_admin_world
from tests.foundation.access_support import AuthorizeFlaggedAdmin


def test_client_list_shows_health_with_critical_clients_first() -> None:
    world = build_admin_world()

    listing = world.testbed.list_clients.run(AdminClientsQuery(user_id=world.admin.id))

    assert int(listing.totals.client_count) == 3
    assert int(listing.matching_count) == 3
    assert listing.next_cursor is None
    assert listing.generated_at == world.testbed.clock.now()
    assert [str(client.name) for client in listing.items] == [
        "Bella Napoli",
        "Funicular VR",
        "Austin Bikes",
    ]
    italian, georgian, american = listing.items
    assert italian.health_status is ClientHealthStatus.CRITICAL
    assert italian.health_issues == [
        ClientHealthIssue.LEADS_ONLY_MODE,
        ClientHealthIssue.PAYMENT_PAST_DUE,
        ClientHealthIssue.NOT_PUBLISHED,
    ]
    assert american.health_status is ClientHealthStatus.ATTENTION
    assert american.health_issues == [ClientHealthIssue.NO_SUBSCRIPTION]
    assert american.subscription_status is None
    assert american.plan_key is PlanKey.CHAT
    assert georgian.health_status is ClientHealthStatus.ATTENTION
    assert georgian.health_issues == [
        ClientHealthIssue.AUTOTESTS_FAILED,
        ClientHealthIssue.TOOL_ERRORS,
    ]
    assert georgian.subscription_status is SubscriptionStatus.TRIALING
    assert int(georgian.published_version_number or 0) == 2
    assert georgian.last_test_score == pytest.approx(3.8)
    assert int(georgian.failed_tests) == 2
    verdict = georgian.autotest_verdict
    assert verdict is not None
    assert (int(verdict.version_number), verdict.is_passed) == (2, False)
    assert (int(verdict.passed_count or 0), int(verdict.scenario_count or 0)) == (1, 3)
    assert int(georgian.handoffs_last_7_days) == 2
    assert int(georgian.open_unanswered_questions) == 1
    assert int(georgian.tool_errors_last_7_days) == 2
    assert int(georgian.used_voice_minutes) == 200
    assert int(georgian.included_voice_minutes) == 400
    assert int(georgian.used_dialogs) == 25
    assert georgian.cost.revenue.currency_code == "GEL"
    # Dollar provider costs reach lari through the euro (dated catalog rates).
    assert georgian.cost.margin is not None
    rate = georgian.cost.exchange_rate
    assert rate is not None
    assert (str(rate.base_currency_code), str(rate.quote_currency_code)) == (
        "USD",
        "GEL",
    )
    assert rate.is_derived is True


def list_names(world: AdminWorld, **query: object) -> list[str]:
    page = world.testbed.list_clients.run(
        AdminClientsQuery.model_validate({"user_id": world.admin.id, **query})
    )
    return [str(client.name) for client in page.items]


def test_client_list_totals_and_filter_choices_cover_every_client() -> None:
    world = build_admin_world()

    listing = world.testbed.list_clients.run(
        AdminClientsQuery(user_id=world.admin.id, health=ClientHealthStatus.CRITICAL)
    )

    assert [str(client.name) for client in listing.items] == ["Bella Napoli"]
    assert int(listing.matching_count) == 1
    assert (
        int(listing.totals.client_count),
        int(listing.totals.critical_count),
        int(listing.totals.attention_count),
        int(listing.totals.healthy_count),
        int(listing.totals.losing_money_count),
    ) == (3, 1, 2, 0, 0)
    assert [str(code) for code in listing.countries] == ["GE", "IT", "US"]
    assert len(listing.niches) >= 1


@pytest.mark.parametrize(
    ("query", "names"),
    [
        ({"health": ClientHealthStatus.ATTENTION}, ["Funicular VR", "Austin Bikes"]),
        ({"country_code": CountryCode("IT")}, ["Bella Napoli"]),
        ({"search": ClientSearchText("BIKES")}, ["Austin Bikes"]),
        (
            {
                "search": ClientSearchText("napoli"),
                "health": ClientHealthStatus.HEALTHY,
            },
            [],
        ),
        (
            {"sort": AdminClientSort.NAME},
            ["Austin Bikes", "Bella Napoli", "Funicular VR"],
        ),
        (
            {"sort": AdminClientSort.USAGE},
            ["Funicular VR", "Bella Napoli", "Austin Bikes"],
        ),
    ],
)
def test_client_list_filters_and_sorts_on_the_server(
    query: dict[str, object],
    names: list[str],
) -> None:
    world = build_admin_world()

    assert list_names(world, **query) == names


def test_client_list_filters_by_status_and_niche() -> None:
    world = build_admin_world()
    stored = world.testbed.business(world.american.id)
    stored.status = BusinessStatus.LIVE
    world.testbed.business_repo.save(stored)

    assert list_names(world, status=BusinessStatus.LIVE) == ["Austin Bikes"]
    assert list_names(world, niche_key=stored.niche_key) == [
        "Bella Napoli",
        "Funicular VR",
        "Austin Bikes",
    ]


def test_client_list_pages_keep_their_place() -> None:
    world = build_admin_world()
    first = world.testbed.list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id,
            sort=AdminClientSort.NAME,
            page=PageRequest(size=PageSize(2)),
        )
    )
    second = world.testbed.list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id,
            sort=AdminClientSort.NAME,
            page=PageRequest(size=PageSize(2), cursor=first.next_cursor),
        )
    )

    assert [str(client.name) for client in first.items] == [
        "Austin Bikes",
        "Bella Napoli",
    ]
    assert first.next_cursor is not None
    assert [str(client.name) for client in second.items] == ["Funicular VR"]
    assert second.next_cursor is None


# margin %, provider cost (micro USD), revenue (minor units), currency
type ClientMoney = tuple[float | None, int, int, str]


class CostOverridingSummarizer(
    UseCaseContract[ClientSummarySource, AdminClientSummary]
):
    """Real client summaries with a cost picked per business name."""

    def __init__(
        self,
        inner: UseCaseContract[ClientSummarySource, AdminClientSummary],
        costs: dict[str, ClientMoney],
    ) -> None:
        self._inner: UseCaseContract[ClientSummarySource, AdminClientSummary] = inner
        self._costs: dict[str, ClientMoney] = costs

    def run(self, input_data: ClientSummarySource) -> AdminClientSummary:
        summary: AdminClientSummary = self._inner.run(input_data)
        margin_percent, provider_cost, revenue, currency = self._costs[
            str(summary.name)
        ]
        cost = summary.cost.model_copy(
            update={
                "margin_percent": (
                    None
                    if margin_percent is None
                    else GrossMarginPercent(margin_percent)
                ),
                "provider_cost_micro_usd": CostMicroUsd(provider_cost),
                "revenue": Money(
                    amount_minor=MoneyAmountMinor(revenue),
                    currency_code=CurrencyCode(currency),
                ),
            }
        )
        return summary.model_copy(update={"cost": cost})


def build_costed_list_clients(world: AdminWorld) -> ListClientsUseCase:
    testbed = world.testbed
    return ListClientsUseCase(
        authorize_platform_admin=AuthorizeFlaggedAdmin(testbed.user_repo),
        business_repo=testbed.business_repo,
        summarize_client=CostOverridingSummarizer(
            testbed.summarize_client,
            {
                "Funicular VR": (None, 9_000_000, 51_700, "GEL"),
                "Bella Napoli": (-40.0, 30_000_000, 17_500, "EUR"),
                "Austin Bikes": (35.0, 1_000_000, 9_900, "EUR"),
            },
        ),
        wall_clock=testbed.clock.wall_clock,
    )


@pytest.mark.parametrize(
    ("sort", "names"),
    [
        # Lowest margin first (losing money on top), unknown margin last.
        (AdminClientSort.MARGIN, ["Bella Napoli", "Austin Bikes", "Funicular VR"]),
        # Most expensive first.
        (AdminClientSort.COST, ["Bella Napoli", "Funicular VR", "Austin Bikes"]),
        # Grouped by currency code, the highest amount first within a currency.
        (AdminClientSort.REVENUE, ["Bella Napoli", "Austin Bikes", "Funicular VR"]),
    ],
)
def test_client_list_sorts_by_money_and_pages_keep_the_order(
    sort: AdminClientSort, names: list[str]
) -> None:
    world = build_admin_world()
    list_clients = build_costed_list_clients(world)

    whole = list_clients.run(AdminClientsQuery(user_id=world.admin.id, sort=sort))
    first = list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id, sort=sort, page=PageRequest(size=PageSize(2))
        )
    )
    second = list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id,
            sort=sort,
            page=PageRequest(size=PageSize(2), cursor=first.next_cursor),
        )
    )

    assert [str(client.name) for client in whole.items] == names
    assert [str(client.name) for client in [*first.items, *second.items]] == names
    assert second.next_cursor is None
