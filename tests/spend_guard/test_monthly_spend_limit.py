"""
The monthly hard stop on top of the daily limits (AI-09): a business kept
under its daily hard limit every day still stops once its month's spend
reaches ten days of it, told and audited once; last month does not count.
"""

import json
from datetime import datetime, timedelta

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendVerdict
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.use_cases.spend_guard.monthly_spend_limit import (
    MONTHLY_HARD_LIMIT_DAYS,
    business_month_start,
)
from tests.spend_guard.spend_world import (
    DAY_START,
    DOLLAR,
    NOON,
    SpendWorld,
    build_spend_world,
    micros,
)

DAILY_HARD: int = 3 * DOLLAR
LAST_MONTH: datetime = DAY_START - timedelta(days=10)


def check(world: SpendWorld) -> SpendVerdict:
    return world.check.run(SpendCheckRequest(business=world.business, now=micros(NOON)))


def month_spent_under_the_daily_limit(world: SpendWorld, total: int) -> None:
    """`total` spent on the earlier days of this month (none of it today)."""

    days: int = total // (DAILY_HARD - 1) + 1
    for day in range(days):
        world.spend(
            UsageKind.LLM_OUTPUT_TOKENS,
            1_000,
            total // days,
            at=NOON - timedelta(days=1 + day % 4, minutes=day),
        )


def test_the_month_starts_on_the_first_in_the_business_time_zone() -> None:
    month, started_at = business_month_start(micros(NOON), TimezoneName("Asia/Tbilisi"))

    assert month == "2026-10"
    assert started_at == micros(datetime.fromisoformat("2026-10-01T00:00:00+04:00"))


def test_past_the_monthly_limit_the_business_stops_and_is_told_once() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=DAILY_HARD)
    month_spent_under_the_daily_limit(world, MONTHLY_HARD_LIMIT_DAYS * DAILY_HARD)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 10, 10_000)

    first = check(world)
    sums_after_first = world.usage_spend.business_sums
    second = check(world)

    assert first.level is SpendLevel.HARD_LIMIT
    assert second.level is SpendLevel.HARD_LIMIT
    # The month's mark settles the second check without summing again.
    assert world.usage_spend.business_sums == sums_after_first
    (entry,) = world.audit_entries()
    assert entry.action is AuditAction.SPEND_LIMIT_REACHED
    (notification,) = world.notifier.notifications
    assert "месячный лимит $30.00" in str(notification.text)
    (job,) = world.jobs.jobs
    assert "reached its hard monthly limit" in json.loads(str(job.payload))["text"]


def test_a_day_without_spend_does_not_sum_the_month() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=DAILY_HARD)
    month_spent_under_the_daily_limit(world, MONTHLY_HARD_LIMIT_DAYS * DAILY_HARD)

    verdict = check(world)

    assert verdict.level is SpendLevel.NORMAL
    assert world.notifier.notifications == []


def test_last_months_spend_does_not_count() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=DAILY_HARD)
    world.spend(
        UsageKind.LLM_OUTPUT_TOKENS,
        1_000,
        MONTHLY_HARD_LIMIT_DAYS * DAILY_HARD,
        at=LAST_MONTH,
    )
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 10, 10_000)

    assert check(world).level is SpendLevel.NORMAL


def test_raising_the_daily_hard_limit_raises_the_monthly_one() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=DAILY_HARD)
    month_spent_under_the_daily_limit(world, MONTHLY_HARD_LIMIT_DAYS * DAILY_HARD)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 10, 10_000)
    assert check(world).level is SpendLevel.HARD_LIMIT

    world.set_limits(soft=DOLLAR, hard=2 * DAILY_HARD)

    assert check(world).level is SpendLevel.NORMAL
