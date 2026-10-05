"""
The admin client list's standings: the periodic job ranks every client in
each order of the list, and the list reads them back.
"""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.client_health import AdminClientSort
from app.schemas.dto.admin import (
    AdminClientPage,
    AdminClientsQuery,
    AdminClientSummary,
    ClientSummarySource,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.client_health.strings import ClientSummarySnapshot
from app.schemas.typings.platform.constrained_integers import PageSize
from app.use_cases.admin.refresh_client_standings_use_case import (
    RefreshClientStandingsUseCase,
)
from tests.billing.admin_world import build_admin_world
from tests.billing.billing_settings import GEORGIA
from tests.billing.client_list_runs import refresh_standings


def names(listing: AdminClientPage) -> list[str]:
    return [str(item.name) for item in listing.items]


def test_the_job_ranks_every_client_in_each_order() -> None:
    world = build_admin_world()

    report = refresh_standings(world.testbed)
    standings = world.testbed.client_standing_repo.get_many(
        [world.georgian.id, world.italian.id, world.american.id]
    )

    assert int(report.processed_count) == 3
    by_name = {str(standing.name): standing for standing in standings.values()}
    assert [
        int(by_name[name].health_position)
        for name in ("Bella Napoli", "Funicular VR", "Austin Bikes")
    ] == [0, 1, 2]
    assert [
        int(by_name[name].name_position)
        for name in ("Austin Bikes", "Bella Napoli", "Funicular VR")
    ] == [0, 1, 2]


def test_a_client_who_signs_up_later_is_listed_after_the_next_refresh() -> None:
    world = build_admin_world()
    query = AdminClientsQuery(user_id=world.admin.id, sort=AdminClientSort.NAME)
    refresh_standings(world.testbed)
    world.testbed.add_business(world.owner, GEORGIA, name="Abanotubani Baths")

    before = world.testbed.list_clients.run(query)
    refresh_standings(world.testbed)
    after = world.testbed.list_clients.run(query)

    assert names(before) == ["Austin Bikes", "Bella Napoli", "Funicular VR"]
    assert names(after)[0] == "Abanotubani Baths"
    assert int(after.totals.client_count) == 4


def test_a_summary_this_release_cannot_read_is_computed_again() -> None:
    world = build_admin_world()
    refresh_standings(world.testbed)
    repo = world.testbed.client_standing_repo
    stored = repo.get_many([world.italian.id])[world.italian.id]
    repo.save_many(
        [stored.model_copy(update={"summary": ClientSummarySnapshot('{"old": 1}')})]
    )

    listing = world.testbed.list_clients.run(AdminClientsQuery(user_id=world.admin.id))

    assert names(listing) == ["Bella Napoli", "Funicular VR", "Austin Bikes"]
    assert listing.items[0].business_id == world.italian.id


class FailingFor(UseCaseContract[ClientSummarySource, AdminClientSummary]):
    """The real summaries, except one client whose summary fails."""

    def __init__(
        self,
        inner: UseCaseContract[ClientSummarySource, AdminClientSummary],
        failing_name: str,
    ) -> None:
        self._inner = inner
        self._failing_name = failing_name

    def run(self, input_data: ClientSummarySource) -> AdminClientSummary:
        if str(input_data.business.name) == self._failing_name:
            raise NotFoundError("The plan of this client is gone.")

        return self._inner.run(input_data)


def test_a_client_whose_summary_fails_keeps_its_standing() -> None:
    world = build_admin_world()
    testbed = world.testbed
    refresh_standings(testbed)
    before = testbed.client_standing_repo.get_many([world.american.id])

    report = refresh_standings(
        testbed,
        RefreshClientStandingsUseCase(
            testbed.business_repo,
            FailingFor(testbed.summarize_client, "Austin Bikes"),
            testbed.client_standing_repo,
            testbed.clock.wall_clock,
        ),
    )
    after = testbed.client_standing_repo.get_many([world.american.id])

    assert int(report.processed_count) == 2
    assert after == before


def test_a_full_client_id_finds_that_client_and_parts_of_names_walk() -> None:
    world = build_admin_world()
    refresh_standings(world.testbed)

    by_id = world.testbed.list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id,
            search=ClientSearchText(str(world.american.id)),
        )
    )
    first = world.testbed.list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id,
            search=ClientSearchText("a"),
            page=PageRequest(size=PageSize(2)),
        )
    )
    second = world.testbed.list_clients.run(
        AdminClientsQuery(
            user_id=world.admin.id,
            search=ClientSearchText("a"),
            page=PageRequest(size=PageSize(2), cursor=first.next_cursor),
        )
    )

    assert names(by_id) == ["Austin Bikes"]
    assert int(first.matching_count) == 3
    assert names(first) == ["Bella Napoli", "Funicular VR"]
    assert names(second) == ["Austin Bikes"]
    assert second.next_cursor is None
