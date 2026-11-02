"""The admin's view of the global pause and the daily budget stop."""

from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.platform_pause import PlatformBrakeReading, PlatformPauseView
from app.schemas.typings.spend.constrained_integers import SpendPercent


def build_platform_pause_view(
    pause: PlatformPauseDocument | None,
    brake: PlatformBrakeReading,
    settings: SpendGuardSettings,
) -> PlatformPauseView:
    spend = brake.spend_micro_usd
    budget = brake.budget_micro_usd
    return PlatformPauseView(
        is_paused=pause is not None and pause.is_paused,
        reason=None if pause is None else pause.reason,
        changed_by=None if pause is None else pause.changed_by,
        changed_at=None if pause is None else pause.changed_at,
        stop_percent=settings.platform_spend_stop_percent,
        budget_used_percent=(
            None
            if spend is None or budget is None
            else SpendPercent(int(spend) * 100 // int(budget))
        ),
        brake=brake.brake,
    )
