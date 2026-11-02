"""The admin's view of the global pause and the daily budget stop."""

from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.spend import PlatformBrake
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.platform_pause import PlatformBrakeReading, PlatformPauseView
from app.schemas.typings.spend.constrained_integers import SpendPercent


def build_platform_pause_view(
    pause: PlatformPauseDocument | None,
    budget_stop: PlatformBrakeReading,
    settings: SpendGuardSettings,
) -> PlatformPauseView:
    """
    The pause as stored and the budget stop's reading (`read_budget_stop`):
    today's share of the budget shows while paused too, and the pause is
    the brake that holds while it lasts.
    """

    is_paused: bool = pause is not None and pause.is_paused
    spend = budget_stop.spend_micro_usd
    budget = budget_stop.budget_micro_usd
    return PlatformPauseView(
        is_paused=is_paused,
        reason=None if pause is None else pause.reason,
        changed_by=None if pause is None else pause.changed_by,
        changed_at=None if pause is None else pause.changed_at,
        stop_percent=settings.platform_spend_stop_percent,
        budget_used_percent=(
            None
            if spend is None or budget is None
            else SpendPercent(int(spend) * 100 // int(budget))
        ),
        brake=PlatformBrake.PAUSED if is_paused else budget_stop.brake,
    )
