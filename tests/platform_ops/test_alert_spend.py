"""
The spend alerts: a spike of today's provider spend against the week
before pages once per cooldown; the budget breaker pages at 80 % of the
platform's daily budget.
"""

import json

from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformAlertStatus
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.spend.constrained_integers import (
    PlatformDailySpendBudgetMicroUsd,
)
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from tests.platform_ops.ops_documents import DAY, MINUTE, NOW
from tests.platform_ops.ops_world import OpsWorld

TICK: JobTick = JobTick(job_name=JobName("platform_alerts"), scheduled_at=NOW)
DOLLAR: int = 1_000_000
BUSINESS: BusinessId = BusinessId()


def spend(world: OpsWorld, cost: int, at: int) -> None:
    moment = Microseconds(at)
    world.usage_events.upsert(
        f"usage-{len(world.usage_events.list_all())}",
        UsageEventDocument(
            business_id=BUSINESS,
            kind=UsageKind.LLM_OUTPUT_TOKENS,
            quantity=UsageQuantity(1_000),
            cost_micro_usd=CostMicroUsd(cost),
            occurred_at=moment,
            created_at=moment,
            updated_at=moment,
        ),
    )


def a_normal_week(world: OpsWorld) -> None:
    """$4 a day for the 7 days before today (08:00 UTC now)."""

    for day in range(1, 8):
        spend(world, 4 * DOLLAR, int(NOW) - day * DAY)


def observe(world: OpsWorld, code: PlatformAlertCode) -> AlertObservation:
    observations = world.checks().run({code: PLATFORM_ALERT_RULES[code]}, NOW)
    (observation,) = observations
    return observation


def spike_lines(world: OpsWorld) -> list[str]:
    return [
        str(json.loads(str(queued.payload))["text"]).splitlines()[0]
        for queued in world.queue.jobs
    ]


def test_a_normal_day_is_no_spike() -> None:
    world = OpsWorld()
    a_normal_week(world)
    spend(world, 12 * DOLLAR, int(NOW) - 60 * MINUTE)  # exactly 3x the mean

    observation = observe(world, PlatformAlertCode.SPEND_SPIKE)

    assert observation.is_firing is False
    assert int(observation.figure) == 12
    assert int(observation.threshold) == 12
    assert "averaged $4.00 a day" in str(observation.detail)


def test_a_quiet_platform_needs_five_dollars_for_a_spike() -> None:
    world = OpsWorld()
    spend(world, 4 * DOLLAR, int(NOW) - MINUTE)  # no week before: any spend

    assert observe(world, PlatformAlertCode.SPEND_SPIKE).is_firing is False


def test_the_spend_spike_fires_once_per_cooldown() -> None:
    world = OpsWorld()
    a_normal_week(world)
    spend(world, 13 * DOLLAR, int(NOW) - 60 * MINUTE)
    use_case = world.alerts_use_case(cooldown_minutes=60)
    rules_run = {PlatformAlertCode.SPEND_SPIKE}

    first = use_case.run(TICK)
    quiet = []
    for _ in range(11):
        world.clock.advance(5 * MINUTE)
        quiet.append(use_case.run(TICK))
    world.clock.advance(5 * MINUTE)
    again = use_case.run(TICK)

    spike = [line for line in spike_lines(world) if "Spend spike" in line]
    assert int(first.processed_count) == 2
    assert [int(report.processed_count) for report in quiet] == [0] * 11
    assert int(again.processed_count) == 2
    assert (
        spike
        == ["[SEV2] FIRING: Spend spike"] * 2 + ["[SEV2] STILL FIRING: Spend spike"] * 2
    )
    [state] = world.alert_state_repo.get_many(list(rules_run))
    assert state.status is PlatformAlertStatus.FIRING
    assert int(state.notification_count) == 2


def test_the_budget_breaker_fires_at_eighty_percent() -> None:
    world = OpsWorld()
    world.spend_budget = PlatformDailySpendBudgetMicroUsd(100 * DOLLAR)
    spend(world, 80 * DOLLAR, int(NOW) - MINUTE)

    at_eighty = observe(world, PlatformAlertCode.SPEND_BUDGET)
    spend(world, 1, int(NOW) - MINUTE)
    past_eighty = observe(world, PlatformAlertCode.SPEND_BUDGET)

    assert (at_eighty.is_firing, int(at_eighty.figure)) == (False, 80)
    assert (past_eighty.is_firing, int(past_eighty.figure)) == (True, 80)
    assert "$80.00 of the $100.00 daily budget" in str(past_eighty.detail)


def test_without_a_budget_the_breaker_stays_quiet() -> None:
    world = OpsWorld()
    spend(world, 500 * DOLLAR, int(NOW) - MINUTE)

    observation = observe(world, PlatformAlertCode.SPEND_BUDGET)

    assert observation.is_firing is False
    assert "PLATFORM_DAILY_SPEND_BUDGET_USD" in str(observation.detail)
