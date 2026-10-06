"""
One API process's request counts: per five-minute slot, 5xx as server
errors, handed to the shared slots on flush and kept when that fails.
"""

from typed_time_provider import Microseconds

from app.contracts.operator_contract import OperatorContract
from app.gateways.metrics.api_availability_tally import ApiAvailabilityTally
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.dto.jobs import JobReport
from app.schemas.dto.service_levels import ApiRequestCounts
from app.use_cases.observability.add_api_request_counts_use_case import (
    AddApiRequestCountsUseCase,
)
from tests.service_levels.sli_world import HOUR_START, MINUTE, SliWorld

API: ServiceLevelSeries = ServiceLevelSeries.API_AVAILABILITY


class UseCaseOperator(OperatorContract[ApiRequestCounts, JobReport]):
    def __init__(self, world: SliWorld) -> None:
        self.use_case = AddApiRequestCountsUseCase(world.slot_repo)
        self.failures: int = 0

    def operate(self, input_data: ApiRequestCounts) -> JobReport:
        if self.failures:
            self.failures -= 1
            raise ConnectionError("database restarting")
        return self.use_case.run(input_data)


def totals(world: SliWorld) -> list[tuple[int, int, int]]:
    return [
        (int(slot.slot_start), int(slot.total), int(slot.good))
        for slot in world.slot_repo.list_window(
            API, Microseconds(0), Microseconds(2**62)
        )
    ]


def test_requests_are_counted_per_slot_with_their_server_errors() -> None:
    world = SliWorld()
    tally = ApiAvailabilityTally(UseCaseOperator(world), world.clock.wall_clock)
    for status in (200, 201, 404, 429, 500):
        tally.count(status)
    world.clock.advance(6 * MINUTE)
    tally.count(503)
    tally.count(200)

    tally.flush()
    tally.flush()  # nothing new: no write

    assert totals(world) == [
        (HOUR_START, 5, 4),
        (HOUR_START + 5 * MINUTE, 2, 1),
    ]


def test_processes_add_up_in_the_shared_slot() -> None:
    world = SliWorld()
    first = ApiAvailabilityTally(UseCaseOperator(world), world.clock.wall_clock)
    second = ApiAvailabilityTally(UseCaseOperator(world), world.clock.wall_clock)
    first.count(200)
    second.count(200)
    second.count(502)

    first.flush()
    second.flush()

    assert totals(world) == [(HOUR_START, 3, 2)]


def test_a_failed_flush_keeps_the_counts_for_the_next_one() -> None:
    world = SliWorld()
    operator = UseCaseOperator(world)
    operator.failures = 1
    tally = ApiAvailabilityTally(operator, world.clock.wall_clock)
    tally.count(200)

    tally.flush()
    assert totals(world) == []
    tally.count(200)
    tally.flush()

    assert totals(world) == [(HOUR_START, 2, 2)]


def test_closing_stops_the_thread_and_flushes_what_is_left() -> None:
    world = SliWorld()
    tally = ApiAvailabilityTally(
        UseCaseOperator(world), world.clock.wall_clock, flush_seconds=3600.0
    )
    tally.start()
    tally.start()  # once per process
    tally.count(200)

    tally.close()

    assert totals(world) == [(HOUR_START, 1, 1)]
