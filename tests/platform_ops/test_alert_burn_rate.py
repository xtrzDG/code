"""
The SLOs' multi-window burn-rate alerts: each rule fires once, stays quiet
through its cooldown and is told again after it; a rule needs both its
windows to burn and its volume floor; stale customer-message slots page
nobody.
"""

import json

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.service_levels import ServiceLevelSlotDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.admin.alerts.alert_texts import ALERT_TITLES
from app.utilities.observability.service_levels import SLOT_MICROSECONDS, slot_start_of
from tests.platform_ops.ops_documents import MINUTE, NOW
from tests.platform_ops.ops_world import OpsWorld

TICK: JobTick = JobTick(job_name=JobName("platform_alerts"), scheduled_at=NOW)
HOUR: int = 60 * MINUTE
INBOUND: ServiceLevelSeries = ServiceLevelSeries.INBOUND_ANSWERED
API: ServiceLevelSeries = ServiceLevelSeries.API_AVAILABILITY
# Per slot: events and good events at 20 times (fast) and 10 times (slow)
# the pace the objective allows (0.5% bad for answers, 0.1% for the API).
BURNS: dict[PlatformAlertCode, tuple[ServiceLevelSeries, int, int]] = {
    PlatformAlertCode.ANSWER_BUDGET_FAST_BURN: (INBOUND, 100, 90),
    PlatformAlertCode.ANSWER_BUDGET_SLOW_BURN: (INBOUND, 100, 95),
    PlatformAlertCode.API_BUDGET_FAST_BURN: (API, 1000, 980),
    PlatformAlertCode.API_BUDGET_SLOW_BURN: (API, 1000, 990),
}


def fill_slots(
    world: OpsWorld,
    series: ServiceLevelSeries,
    total: int,
    good: int,
    since: int,
    until: int,
) -> None:
    """Every slot that starts from `since` up to `until` holds these counts."""

    start = int(slot_start_of(since))
    while start < until:
        world.slot_repo.save(
            ServiceLevelSlotDocument(
                series=series,
                slot_start=Microseconds(start),
                total=ServiceLevelEventCount(total),
                good=ServiceLevelEventCount(good),
            )
        )
        start += SLOT_MICROSECONDS


def burn_until_now(
    world: OpsWorld, series: ServiceLevelSeries, total: int, good: int
) -> None:
    fill_slots(world, series, total, good, world.clock.now - 7 * HOUR, world.clock.now)


def lines_of(world: OpsWorld, code: PlatformAlertCode) -> list[str]:
    title: str = ALERT_TITLES[code.value]
    lines = [
        str(json.loads(str(queued.payload))["text"]).splitlines()[0]
        for queued in world.queue.jobs
    ]
    return [line for line in lines if line.endswith(f": {title}")]


@pytest.mark.parametrize("code", list(BURNS))
def test_each_burn_rate_rule_fires_once_per_cooldown(code: PlatformAlertCode) -> None:
    world = OpsWorld()
    series, total, good = BURNS[code]
    use_case = world.alerts_use_case(cooldown_minutes=60)
    severity: str = PLATFORM_ALERT_RULES[code].severity.value.upper()

    burn_until_now(world, series, total, good)
    use_case.run(TICK)
    for _ in range(11):
        world.clock.advance(5 * MINUTE)
        burn_until_now(world, series, total, good)
        use_case.run(TICK)
    within_cooldown = lines_of(world, code)
    world.clock.advance(5 * MINUTE)
    burn_until_now(world, series, total, good)
    use_case.run(TICK)

    assert within_cooldown == [f"[{severity}] FIRING: {ALERT_TITLES[code.value]}"] * 2
    assert (
        lines_of(world, code)[2:]
        == [f"[{severity}] STILL FIRING: {ALERT_TITLES[code.value]}"] * 2
    )
    [state] = world.alert_state_repo.get_many([code])
    assert int(state.figure) > int(PLATFORM_ALERT_RULES[code].threshold)


def test_a_slow_burn_does_not_page_as_a_fast_one() -> None:
    world = OpsWorld()
    burn_until_now(world, API, 1000, 990)  # 10 times the sustainable pace

    world.alerts_use_case().run(TICK)

    assert lines_of(world, PlatformAlertCode.API_BUDGET_SLOW_BURN) != []
    assert lines_of(world, PlatformAlertCode.API_BUDGET_FAST_BURN) == []


def test_a_burn_that_stopped_in_the_short_window_is_quiet() -> None:
    world = OpsWorld()
    now: int = world.clock.now
    fill_slots(world, API, 1000, 900, now - HOUR, now - 5 * MINUTE)
    fill_slots(world, API, 1000, 1000, now - 5 * MINUTE, now + 1)

    world.alerts_use_case().run(TICK)

    assert lines_of(world, PlatformAlertCode.API_BUDGET_FAST_BURN) == []


def test_a_burn_below_the_volume_floor_is_quiet() -> None:
    world = OpsWorld()
    now: int = world.clock.now
    # Three customer messages in the last quarter hour, each one late.
    fill_slots(world, INBOUND, 1, 0, now - 15 * MINUTE, now + 1)

    world.alerts_use_case().run(TICK)

    observed = [
        lines_of(world, code)
        for code in (
            PlatformAlertCode.ANSWER_BUDGET_FAST_BURN,
            PlatformAlertCode.ANSWER_BUDGET_SLOW_BURN,
        )
    ]
    assert observed == [[], []]


def test_customer_message_slots_end_with_the_newest_judged_slot() -> None:
    world = OpsWorld()
    now: int = world.clock.now
    # record_sli judged slots up to 10 minutes ago; the burn is in them.
    fill_slots(world, INBOUND, 100, 80, now - HOUR, now - 10 * MINUTE)

    world.alerts_use_case().run(TICK)
    fired = lines_of(world, PlatformAlertCode.ANSWER_BUDGET_FAST_BURN)
    world.clock.advance(2 * HOUR)  # record_sli stopped: no new slots
    world.alerts_use_case().run(TICK)

    assert fired == ["[SEV1] FIRING: Answer budget burns fast"] * 2
    assert (
        lines_of(world, PlatformAlertCode.ANSWER_BUDGET_FAST_BURN)[2:]
        == ["[SEV1] RESOLVED: Answer budget burns fast"] * 2
    )
