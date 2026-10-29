"""
The spend guard's parts: the cheaper model, pricing by provider, the
business's day, and one announcement when processes pass a limit at once.
"""

import threading

from app.contracts.repositories.spend_guard_repositories import (
    SpendLimitMarkRepoContract,
)
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.spend import SpendLevel, SpendProvider
from app.schemas.domain.business_limits import SpendLimitMarkDocument
from app.schemas.dto.spend_guard import SpendCheckRequest, UsageKindTotal
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantityTotal,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.spend.constrained_strings import SpendDay
from app.schemas.typings.spend.prefixed_id import SpendLimitMarkId
from app.utilities.spend.cheaper_models import cheaper_model_of
from app.utilities.spend.spend_days import business_day, utc_day
from app.utilities.spend.spend_notice_texts import describe_usd
from app.utilities.spend.spend_pricing import price_usage, total_spend
from tests.spend_guard.spend_world import DOLLAR, NOON, build_spend_world, micros


def test_the_cheaper_model_stays_with_the_assistants_provider() -> None:
    def cheaper(model: str, configured: str | None = None) -> str:
        return str(
            cheaper_model_of(
                LlmModelId(model),
                None if configured is None else LlmModelId(configured),
            )
        )

    assert cheaper("gpt-5-mini") == "gpt-5-nano"
    assert cheaper("claude-opus-5-5") == "claude-haiku-4-5"
    assert cheaper("scripted") == "scripted"
    assert cheaper("gpt-5-mini", configured="gpt-5-mini-2025-08-07") == (
        "gpt-5-mini-2025-08-07"
    )
    # Another provider's model cannot continue the conversation's turns.
    assert cheaper("gpt-5-mini", configured="claude-haiku-4-5") == "gpt-5-nano"
    assert cheaper("mystery-model") == "mystery-model"


def total(kind: UsageKind, quantity: int, cost: int) -> UsageKindTotal:
    return UsageKindTotal(
        kind=kind,
        quantity=UsageQuantityTotal(quantity),
        cost_micro_usd=CostMicroUsd(cost),
    )


def test_usage_is_priced_by_provider_with_planned_prices_for_missing_figures() -> None:
    providers = price_usage(
        [
            total(UsageKind.LLM_INPUT_TOKENS, 10_000, 2_500),
            total(UsageKind.LLM_OUTPUT_TOKENS, 1_000, 2_000),
            # A reported call costs what the voice platform said when more.
            total(UsageKind.VOICE_SECONDS, 60, 200_000),
            total(UsageKind.TRANSFER_SECONDS, 30, 0),
            total(UsageKind.WHATSAPP_TEMPLATE, 2, 0),
            total(UsageKind.WHATSAPP_REPLY, 5, 0),
            total(UsageKind.DIALOG, 3, 0),
        ]
    )

    assert {item.provider: int(item.spend_micro_usd) for item in providers} == {
        SpendProvider.LANGUAGE_MODEL: 4_500,
        SpendProvider.VOICE: 200_000,
        SpendProvider.TELEPHONY: 9_990,
        SpendProvider.WHATSAPP: 80_000,
    }
    assert int(total_spend(providers)) == 294_490


def test_the_day_is_the_business_own_and_the_platform_one_is_utc() -> None:
    day, started = business_day(micros(NOON), TimezoneName("America/New_York"))
    platform_day, platform_started = utc_day(micros(NOON))

    # 12:00 in Tbilisi is 04:00 in New York, 08:00 UTC, the same date.
    assert (day, platform_day) == (SpendDay("2026-10-05"), SpendDay("2026-10-05"))
    assert int(started) == 1_791_172_800_000_000  # 2026-10-05 04:00 UTC
    assert int(platform_started) == 1_791_158_400_000_000  # 2026-10-05 00:00 UTC


def test_dollars_are_shown_with_cents() -> None:
    assert describe_usd(0) == "$0.00"
    assert describe_usd(1_234_567) == "$1.23"
    assert describe_usd(5_000) == "$0.01"


class RacingMarks(SpendLimitMarkRepoContract):
    """Holds every insert until both processes reach it, then lets them race."""

    def __init__(self, inner: SpendLimitMarkRepoContract) -> None:
        self._inner: SpendLimitMarkRepoContract = inner
        self._barrier: threading.Barrier = threading.Barrier(2, timeout=10)

    def get(
        self, business_id: BusinessId, mark_id: SpendLimitMarkId
    ) -> SpendLimitMarkDocument | None:
        return self._inner.get(business_id, mark_id)

    def insert_if_absent(self, mark: SpendLimitMarkDocument) -> bool:
        self._barrier.wait()
        return self._inner.insert_if_absent(mark)

    def list_by_day(self, day: SpendDay) -> list[SpendLimitMarkDocument]:
        return self._inner.list_by_day(day)


def test_two_processes_passing_the_hard_limit_at_once_announce_it_once() -> None:
    world = build_spend_world(wrap_marks=RacingMarks)
    world.set_limits(soft=DOLLAR, hard=2 * DOLLAR)
    world.spend(UsageKind.LLM_OUTPUT_TOKENS, 9_000, 3 * DOLLAR)
    levels: list[SpendLevel] = []

    def turn() -> None:
        verdict = world.check.run(
            SpendCheckRequest(business=world.business, now=micros(NOON))
        )
        levels.append(verdict.level)

    threads = [threading.Thread(target=turn) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert levels == [SpendLevel.HARD_LIMIT, SpendLevel.HARD_LIMIT]
    assert len(world.audit_entries()) == 1
    assert len(world.notifier.notifications) == 1
    assert len(world.jobs.jobs) == 1
