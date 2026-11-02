"""The global pause and the daily budget stop over the spend world."""

from datetime import datetime

from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.spend.constrained_integers import (
    PlatformDailySpendBudgetMicroUsd,
    PlatformSpendStopPercent,
)
from app.schemas.typings.spend.constrained_strings import PlatformPauseReason
from app.schemas.typings.users.prefixed_id import UserId
from tests.spend_guard.spend_world import DOLLAR, NOON, SpendWorld, micros


def budget_settings(budget_usd: int, stop_percent: int = 100) -> SpendGuardSettings:
    return SpendGuardSettings(
        platform_daily_budget_micro_usd=PlatformDailySpendBudgetMicroUsd(
            budget_usd * DOLLAR
        ),
        platform_spend_stop_percent=PlatformSpendStopPercent(stop_percent),
    )


def pause(world: SpendWorld, is_paused: bool = True) -> None:
    now = micros(NOON)
    world.pauses.save(
        PlatformPauseDocument(
            is_paused=is_paused,
            reason=PlatformPauseReason("Model answers in the wrong language"),
            changed_by=UserId(),
            changed_at=now,
            created_at=now,
            updated_at=now,
        )
    )


def spend_elsewhere(world: SpendWorld, cost_micro_usd: int, at: datetime = NOON) -> None:
    """Spend of another business: only the platform's sum sees it."""

    moment = micros(at)
    world.usage_events.append(
        UsageEventDocument(
            business_id=BusinessId(),
            kind=UsageKind.LLM_TOKENS_INPUT,
            quantity=UsageQuantity(1_000),
            cost_micro_usd=CostMicroUsd(cost_micro_usd),
            occurred_at=moment,
            created_at=moment,
            updated_at=moment,
        )
    )
