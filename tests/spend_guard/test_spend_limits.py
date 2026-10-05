"""
The spend guard's verdicts with fixed prices: under, past the soft and past
the hard daily limit of a business, told and audited once.
"""

import json
from datetime import timedelta

from app.schemas.constants.billing import PlanKey, UsageKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendVerdict
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from tests.spend_guard.spend_world import (
    CHAT_PLANNED_DAILY_MICRO_USD,
    DAY_START,
    DOLLAR,
    NOON,
    SpendWorld,
    build_spend_world,
    micros,
)

GPT_MINI: LlmModelId = LlmModelId("gpt-5-mini")


def check(world: SpendWorld, model_id: LlmModelId | None = GPT_MINI) -> SpendVerdict:
    return world.check.run(
        SpendCheckRequest(business=world.business, now=micros(NOON), model_id=model_id)
    )


def test_the_plan_defaults_are_multiples_of_its_planned_daily_cost() -> None:
    world = build_spend_world(PlanKey.CHAT)

    verdict = check(world)

    assert verdict.level is SpendLevel.NORMAL
    assert verdict.day == "2026-10-05"
    assert int(verdict.limits.soft_limit_micro_usd) == 5 * CHAT_PLANNED_DAILY_MICRO_USD
    assert int(verdict.limits.hard_limit_micro_usd) == 15 * CHAT_PLANNED_DAILY_MICRO_USD
    assert verdict.limits.is_custom is False
    assert verdict.cheaper_model_id is None


def test_under_the_soft_limit_nothing_happens() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=3 * DOLLAR)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 1000, 999_999)

    verdict = check(world)

    assert verdict.level is SpendLevel.NORMAL
    assert int(verdict.spend_micro_usd) == 999_999
    assert world.notifier.notifications == []
    assert world.jobs.jobs == []


def test_past_the_soft_limit_the_turn_uses_the_cheaper_model_and_tells_once() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=3 * DOLLAR)
    world.spend(UsageKind.LLM_INPUT_TOKENS, 40_000, 600_000)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 2_000, 400_000)

    first = check(world)
    second = check(world)

    assert first.level is SpendLevel.SOFT_LIMIT
    assert first.cheaper_model_id == "gpt-5-nano"
    assert second.level is SpendLevel.SOFT_LIMIT
    (notification,) = world.notifier.notifications
    assert str(notification.contact.address) == "owner@salobie.example"
    assert "Salobie Bia" in str(notification.text)
    assert "$1.00" in str(notification.text)
    assert "облегчённой модели" in str(notification.text)  # the owner's Russian
    (job,) = world.jobs.jobs
    assert job.name == "send_platform_alert"
    assert (
        "passed its soft daily limit ($1.00 of $1.00)"
        in json.loads(str(job.payload))["text"]
    )
    assert world.audit_entries() == []


def test_past_the_hard_limit_the_business_takes_messages_only_audited_once() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=3 * DOLLAR)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 9_000, 3 * DOLLAR + 1)

    first = check(world)
    sums_after_first = world.usage_spend.business_sums
    second = check(world, model_id=None)

    assert first.level is SpendLevel.HARD_LIMIT
    assert first.cheaper_model_id is None
    assert second.level is SpendLevel.HARD_LIMIT
    # The day's hard mark settles the second check without summing again.
    assert world.usage_spend.business_sums == sums_after_first
    (entry,) = world.audit_entries()
    assert entry.action is AuditAction.SPEND_LIMIT_REACHED
    assert entry.actor_id is None
    (notification,) = world.notifier.notifications
    assert "больше не отвечает сам" in str(notification.text)
    (job,) = world.jobs.jobs
    assert (
        "reached its hard daily limit ($3.00 of $3.00)"
        in json.loads(str(job.payload))["text"]
    )


def test_raising_the_hard_limit_lets_the_assistant_answer_again() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=3 * DOLLAR)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 9_000, 4 * DOLLAR)
    assert check(world).level is SpendLevel.HARD_LIMIT

    world.set_limits(soft=DOLLAR, hard=10 * DOLLAR)

    assert check(world).level is SpendLevel.SOFT_LIMIT
    assert len(world.audit_entries()) == 1


def test_missing_voice_figures_are_priced_with_the_planned_unit_cost() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=3 * DOLLAR)
    # Ten minutes of calls whose report has not arrived: 600 s * 1,500.
    world.spend(UsageKind.VOICE_SECONDS, 600, 0)

    verdict = check(world, model_id=None)

    assert int(verdict.spend_micro_usd) == 900_000
    assert verdict.level is SpendLevel.NORMAL


def test_yesterday_in_the_business_time_zone_does_not_count() -> None:
    world = build_spend_world()
    world.set_limits(soft=DOLLAR, hard=3 * DOLLAR)
    world.spend(
        UsageKind.LLM_OUTPUT_TOKENS,
        9_000,
        5 * DOLLAR,
        at=DAY_START - timedelta(seconds=1),
    )
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 100, 10_000, at=DAY_START)

    verdict = check(world)

    assert verdict.level is SpendLevel.NORMAL
    assert int(verdict.spend_micro_usd) == 10_000


def test_a_soft_limit_above_the_hard_one_is_held_at_the_hard_one() -> None:
    world = build_spend_world()
    world.set_limits(soft=5 * DOLLAR, hard=2 * DOLLAR)

    verdict = check(world)

    assert int(verdict.limits.soft_limit_micro_usd) == 2 * DOLLAR
    assert verdict.limits.is_custom is True
