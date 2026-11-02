"""
The spend alerts' checks: today's platform spend (UTC) against the daily
mean of the 7 days before (`spend_spike`), against the daily budget's
warning share (`spend_budget`) and against the share where every
assistant stops (`spend_budget_stop`). The spike's figures are whole US
dollars, the budget's percents of the budget.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.spend_guard_repositories import (
    UsageSpendRepoContract,
)
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.dto.spend_guard import PlatformSpendFigures
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
)
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.schemas.configurations.spend_guard_settings import (
    DEFAULT_PLATFORM_SPEND_STOP_PERCENT,
)
from app.schemas.typings.spend.constrained_integers import (
    PlatformDailySpendBudgetMicroUsd,
    PlatformSpendStopPercent,
)
from app.utilities.spend.platform_spend import WEEK_DAYS, read_platform_spend
from app.utilities.spend.spend_notice_texts import describe_usd

MICRO_USD_PER_USD: int = 1_000_000


class SpendAlertChecks:
    """
    The checks read the same two indexed sums of the usage events
    (`read_platform_spend`); the budget is PLATFORM_DAILY_SPEND_BUDGET_USD
    (no budget: the budget alerts never fire), the stop
    PLATFORM_DAILY_SPEND_STOP_PERCENT of it.
    """

    def __init__(
        self,
        usage_spend_repo: UsageSpendRepoContract,
        daily_budget_micro_usd: PlatformDailySpendBudgetMicroUsd | None,
        stop_percent: PlatformSpendStopPercent = PlatformSpendStopPercent(
            DEFAULT_PLATFORM_SPEND_STOP_PERCENT
        ),
    ) -> None:
        self._usage: UsageSpendRepoContract = usage_spend_repo
        self._budget: PlatformDailySpendBudgetMicroUsd | None = daily_budget_micro_usd
        self._stop_percent: PlatformSpendStopPercent = stop_percent

    def spend_spike(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        """
        Fires when today's spend is above `threshold` times the week's daily
        mean (compared in micro-dollars, exactly) and at least
        `volume_floor` dollars, so a quiet platform's first dollar is no
        spike.
        """

        figures: PlatformSpendFigures = read_platform_spend(self._usage, now)
        today: int = int(figures.total_micro_usd)
        week: int = int(figures.week_total_micro_usd)
        multiple: int = int(rule.threshold)
        floor: int = int(rule.volume_floor) * MICRO_USD_PER_USD
        spike_from: int = max(floor, -(-multiple * week // WEEK_DAYS))
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(today // MICRO_USD_PER_USD),
            threshold=AlertThreshold(-(-spike_from // MICRO_USD_PER_USD)),
            unit=rule.unit,
            detail=AlertDetailText(
                f"Provider spend today (UTC) is {describe_usd(today)}; the 7 "
                f"days before averaged {describe_usd(week // WEEK_DAYS)} a day."
            ),
            is_firing=today >= floor and today * WEEK_DAYS > multiple * week,
        )

    def spend_budget(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        """Fires when today's spend passed `threshold` % of the daily budget."""

        if self._budget is None:
            return AlertObservation(
                code=rule.code,
                figure=AlertFigure(0),
                threshold=rule.threshold,
                unit=rule.unit,
                detail=AlertDetailText(
                    "No daily budget is set (PLATFORM_DAILY_SPEND_BUDGET_USD)."
                ),
                is_firing=False,
            )

        today: int = int(read_platform_spend(self._usage, now).total_micro_usd)
        budget: int = int(self._budget)
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(today * 100 // budget),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(
                f"Provider spend today (UTC) is {describe_usd(today)} of the "
                f"{describe_usd(budget)} daily budget."
            ),
            is_firing=today * 100 > int(rule.threshold) * budget,
        )

    def spend_budget_stop(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        """
        Fires from the stop share of the daily budget on: every assistant
        then hands customers to the team until UTC midnight (the spend
        guard stops on the same reading); the threshold shown is the stop.
        """

        stop: int = int(self._stop_percent)
        if self._budget is None:
            return AlertObservation(
                code=rule.code,
                figure=AlertFigure(0),
                threshold=AlertThreshold(stop),
                unit=rule.unit,
                detail=AlertDetailText(
                    "No daily budget is set (PLATFORM_DAILY_SPEND_BUDGET_USD): "
                    "nothing stops the assistants."
                ),
                is_firing=False,
            )

        today: int = int(read_platform_spend(self._usage, now).total_micro_usd)
        budget: int = int(self._budget)
        is_stopped: bool = today * 100 >= stop * budget
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(today * 100 // budget),
            threshold=AlertThreshold(stop),
            unit=rule.unit,
            detail=AlertDetailText(
                f"Provider spend today (UTC) is {describe_usd(today)} of the "
                f"{describe_usd(budget)} daily budget; assistants stop at {stop}%"
                + (
                    " and hand customers to the team until UTC midnight."
                    if is_stopped
                    else "."
                )
            ),
            is_firing=is_stopped,
        )
