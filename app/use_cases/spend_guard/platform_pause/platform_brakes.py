"""
Whether a platform brake holds every assistant back now, whatever each
business spent: a platform admin's global pause, else the daily budget
stop (today's provider spend, UTC, at PLATFORM_DAILY_SPEND_STOP_PERCENT of
PLATFORM_DAILY_SPEND_BUDGET_USD). No budget set: no stop.
"""

from typed_time_provider import Microseconds

from app.contracts.platform_safety import (
    PlatformPauseRepoContract,
    PlatformSpendGaugeContract,
)
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.spend import PlatformBrake
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.platform_pause import PlatformBrakeReading
from app.schemas.typings.billing.constrained_integers import CostMicroUsd


def read_platform_brake(
    pause_repo: PlatformPauseRepoContract,
    spend_gauge: PlatformSpendGaugeContract,
    settings: SpendGuardSettings,
    now: Microseconds,
) -> PlatformBrakeReading:
    """
    The brake that holds now for a model turn or a call: the pause first
    (then the budget is not read), else the budget stop with its reading.
    """

    pause: PlatformPauseDocument | None = pause_repo.get()
    if pause is not None and pause.is_paused:
        return PlatformBrakeReading(brake=PlatformBrake.PAUSED)

    return read_budget_stop(spend_gauge, settings, now)


def read_budget_stop(
    spend_gauge: PlatformSpendGaugeContract,
    settings: SpendGuardSettings,
    now: Microseconds,
) -> PlatformBrakeReading:
    """
    The daily budget stop alone (BUDGET_STOP or no brake) with today's
    spend and the budget; nothing to read without a budget.
    """

    budget = settings.platform_daily_budget_micro_usd
    if budget is None:
        return PlatformBrakeReading()

    spend: CostMicroUsd = spend_gauge.spend_today(now)
    is_stopped: bool = int(spend) * 100 >= int(
        settings.platform_spend_stop_percent
    ) * int(budget)
    return PlatformBrakeReading(
        brake=PlatformBrake.BUDGET_STOP if is_stopped else None,
        spend_micro_usd=spend,
        budget_micro_usd=CostMicroUsd(int(budget)),
    )
