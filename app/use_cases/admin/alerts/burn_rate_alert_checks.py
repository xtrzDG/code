"""
The checks of the burn-rate rules (`burn_rate_rules.py`): each sums the
service level slots of its series over the rule's long and short window
and compares both burn rates with the threshold. The windows end with the
newest slot of the series: customer messages are judged a little after
their slot ends (`record_sli`), API requests are counted as they come. A
series whose newest slot is older than the long window has no figure (the
job that writes it stopped; the stale worker alert covers that).
"""

from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.service_levels import ServiceLevelSlotRepoContract
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.service_levels import ServiceLevelSlotDocument
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.dto.service_levels import ServiceLevelTally
from app.schemas.typings.monitoring.constrained_integers import AlertFigure
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.use_cases.admin.alerts.alert_checks import AlertCheck
from app.utilities.observability.service_levels import (
    OBJECTIVES,
    SLOT_MICROSECONDS,
    burn_rate_percent,
    sum_slots,
)

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000
PERCENT: int = 100
SERIES_OF: Mapping[PlatformAlertCode, ServiceLevelSeries] = {
    PlatformAlertCode.ANSWER_BUDGET_FAST_BURN: ServiceLevelSeries.INBOUND_ANSWERED,
    PlatformAlertCode.ANSWER_BUDGET_SLOW_BURN: ServiceLevelSeries.INBOUND_ANSWERED,
    PlatformAlertCode.API_BUDGET_FAST_BURN: ServiceLevelSeries.API_AVAILABILITY,
    PlatformAlertCode.API_BUDGET_SLOW_BURN: ServiceLevelSeries.API_AVAILABILITY,
}
EVENTS_OF: Mapping[ServiceLevelSeries, tuple[str, str]] = {
    ServiceLevelSeries.INBOUND_ANSWERED: (
        "customer messages",
        "were not answered within 60 s",
    ),
    ServiceLevelSeries.API_AVAILABILITY: ("API requests", "failed with a 5xx"),
}


class BurnRateAlertChecks:
    def __init__(self, slot_repo: ServiceLevelSlotRepoContract) -> None:
        self._slots: ServiceLevelSlotRepoContract = slot_repo

    def checks(self) -> Mapping[PlatformAlertCode, AlertCheck]:
        return {code: self.burn for code in SERIES_OF}

    def burn(self, rule: PlatformAlertRule, now: Microseconds) -> AlertObservation:
        series: ServiceLevelSeries = SERIES_OF[rule.code]
        window: int = int(rule.window_minutes) * MICROSECONDS_PER_MINUTE
        short_minutes: int = int(rule.short_window_minutes or rule.window_minutes)
        latest: ServiceLevelSlotDocument | None = self._slots.find_latest(series)
        end: int = (
            int(now)
            if latest is None
            else min(int(now), int(latest.slot_start) + SLOT_MICROSECONDS)
        )
        if end <= int(now) - window:
            return quiet(rule, f"No {EVENTS_OF[series][0]} measured lately.")

        long: ServiceLevelTally = self._tally(series, end - window, end)
        short: ServiceLevelTally = self._tally(
            series, end - short_minutes * MICROSECONDS_PER_MINUTE, end
        )
        objective = OBJECTIVES[series]
        long_rate: int = int(burn_rate_percent(long, objective))
        short_rate: int = int(burn_rate_percent(short, objective))
        threshold: int = int(rule.threshold)
        events, missed = EVENTS_OF[series]
        bad: int = int(long.total) - int(long.good)
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(long_rate),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(
                f"{bad} of {int(long.total)} {events} {missed} in the last "
                f"{int(rule.window_minutes)} min: the error budget burns "
                f"{long_rate / PERCENT:.1f} times as fast as 28 days allow "
                f"({short_rate / PERCENT:.1f} times in the last {short_minutes} "
                "min)."
            ),
            is_firing=(
                int(long.total) >= int(rule.volume_floor)
                and long_rate > threshold
                and short_rate > threshold
            ),
        )

    def _tally(
        self, series: ServiceLevelSeries, since: int, until: int
    ) -> ServiceLevelTally:
        return sum_slots(
            series,
            self._slots.list_window(series, Microseconds(since), Microseconds(until)),
        )


def burn_rate_alert_checks(
    slot_repo: ServiceLevelSlotRepoContract,
) -> Mapping[PlatformAlertCode, AlertCheck]:
    """The checks of the burn-rate rules by code (for `PlatformAlertChecks`)."""

    return BurnRateAlertChecks(slot_repo).checks()


def quiet(rule: PlatformAlertRule, detail: str) -> AlertObservation:
    return AlertObservation(
        code=rule.code,
        figure=AlertFigure(0),
        threshold=rule.threshold,
        unit=rule.unit,
        detail=AlertDetailText(detail),
        is_firing=False,
    )
