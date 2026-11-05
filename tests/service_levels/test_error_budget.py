"""
The error budgets of /admin/system: what is left of each objective's
budget over 28 days of hourly rows, the last hour's burn rate from the
slots, the answer latency hours, and platform admins only.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.service_levels import ServiceLevelHourDocument
from app.schemas.dto.service_levels import (
    ErrorBudgetQuery,
    ErrorBudgetView,
    ObjectiveBudgetView,
    ServiceLevelTally,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.observability.constrained_floats import (
    ServiceLevelObjective,
)
from app.schemas.typings.observability.constrained_integers import (
    AnswerLatencyP95Milliseconds,
    ServiceLevelEventCount,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.observability.get_error_budget_use_case import (
    GetErrorBudgetUseCase,
)
from app.utilities.observability.service_levels import (
    budget_left_permille,
    burn_rate_percent,
)
from tests.platform_ops.ops_world import ADMIN, AdminsOnly
from tests.service_levels.sli_world import HOUR, HOUR_START, MINUTE, SliWorld

API: ServiceLevelSeries = ServiceLevelSeries.API_AVAILABILITY
INBOUND: ServiceLevelSeries = ServiceLevelSeries.INBOUND_ANSWERED


def tally(total: int, good: int) -> ServiceLevelTally:
    return ServiceLevelTally(
        series=API,
        total=ServiceLevelEventCount(total),
        good=ServiceLevelEventCount(good),
    )


def hour_row(
    offset_hours: int,
    inbound: tuple[int, int] = (0, 0),
    api: tuple[int, int] = (0, 0),
    p95_ms: int | None = None,
) -> ServiceLevelHourDocument:
    return ServiceLevelHourDocument(
        hour_start=Microseconds(HOUR_START + offset_hours * HOUR),
        inbound_messages=ServiceLevelEventCount(inbound[0]),
        inbound_in_time=ServiceLevelEventCount(inbound[1]),
        api_requests=ServiceLevelEventCount(api[0]),
        api_server_errors=ServiceLevelEventCount(api[1]),
        reply_p95_ms=(None if p95_ms is None else AnswerLatencyP95Milliseconds(p95_ms)),
    )


def budget(world: SliWorld, user_id: UserId = ADMIN) -> ErrorBudgetView:
    return GetErrorBudgetUseCase(
        AdminsOnly(), world.slot_repo, world.hour_repo, world.clock.wall_clock
    ).run(ErrorBudgetQuery(user_id=user_id))


def objective(view: ErrorBudgetView, series: ServiceLevelSeries) -> ObjectiveBudgetView:
    return next(item for item in view.objectives if item.series is series)


def test_burn_rate_is_the_bad_share_over_the_allowed_share() -> None:
    three_nines = ServiceLevelObjective(0.999)

    assert int(burn_rate_percent(tally(0, 0), three_nines)) == 0
    assert int(burn_rate_percent(tally(1000, 1000), three_nines)) == 0
    assert int(burn_rate_percent(tally(1000, 999), three_nines)) == 100
    assert int(burn_rate_percent(tally(1000, 985), three_nines)) == 1500


def test_budget_left_falls_below_zero_when_overspent() -> None:
    three_nines = ServiceLevelObjective(0.999)

    assert int(budget_left_permille(tally(0, 0), three_nines)) == 1000
    assert int(budget_left_permille(tally(10_000, 9_995), three_nines)) == 500
    assert int(budget_left_permille(tally(10_000, 9_980), three_nines)) == -1000


def test_an_empty_platform_has_whole_budgets_and_no_rows() -> None:
    view = budget(SliWorld())

    assert [item.series for item in view.objectives] == list(ServiceLevelSeries)
    assert all(int(item.budget_left_permille) == 1000 for item in view.objectives)
    assert view.measured_since is None and view.measured_until is None
    assert view.latency.last_hour_p95_ms is None
    assert int(view.latency.measured_hours) == 0


def test_the_budget_sums_28_days_of_rows_and_the_last_hour_of_slots() -> None:
    world = SliWorld(now=HOUR_START + 30 * 24 * HOUR + 20 * MINUTE)
    world.hour_repo.save(hour_row(0, inbound=(1000, 0)))  # older than 28 days
    for offset in range(5 * 24, 30 * 24):
        world.hour_repo.save(
            hour_row(
                offset,
                inbound=(10, 10),
                api=(100, 0),
                p95_ms=20_000 if offset % 24 == 0 else 4_000,
            )
        )
    world.hour_repo.save(hour_row(30 * 24 - 1, inbound=(200, 199), api=(1000, 1)))
    world.slot_repo.add(
        API,
        Microseconds(world.now - 10 * MINUTE),
        ServiceLevelEventCount(1000),
        ServiceLevelEventCount(985),
    )

    view = budget(world)

    inbound = objective(view, INBOUND)
    assert int(inbound.events) == 10 * (24 * 25 - 1) + 200
    assert int(inbound.good_events) == int(inbound.events) - 1
    assert 0 < int(inbound.budget_left_permille) < 1000
    api = objective(view, API)
    assert int(api.events) == 100 * (24 * 25 - 1) + 1000
    assert int(api.burn_rate_last_hour_percent) == 1500
    assert int(objective(view, INBOUND).burn_rate_last_hour_percent) == 0
    assert view.measured_since == Microseconds(HOUR_START + 5 * 24 * HOUR)
    assert view.measured_until == Microseconds(HOUR_START + 30 * 24 * HOUR)
    assert int(view.latency.measured_hours) == 24 * 25 - 1
    assert int(view.latency.hours_over_target) == 25
    assert view.latency.last_hour_p95_ms is None  # the newest row measured none


def test_only_platform_admins_see_the_budget() -> None:
    with pytest.raises(ApplicationError):
        budget(SliWorld(), UserId())
