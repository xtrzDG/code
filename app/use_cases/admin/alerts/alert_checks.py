import logging
from collections.abc import Callable, Mapping

from typed_time_provider import Microseconds

from app.contracts.monitoring import (
    PlatformActivityRepoContract,
    SignalCounterAdapterContract,
    SystemHealthRepoContract,
)
from app.contracts.repositories.quality_repositories import QualityTotalsRepoContract
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
)
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.use_cases.admin.alerts.alert_texts import describe_duration, describe_percent
from app.use_cases.admin.alerts.data_task_alert_checks import DataTaskAlertChecks
from app.use_cases.admin.alerts.spend_alert_checks import SpendAlertChecks
from app.use_cases.admin.alerts.stale_workers import (
    find_stale_workers,
    pulse_age_seconds,
)
from app.utilities.quality.quality_trend import describe_average, drop_percent

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_MINUTE: int = 60 * MICROSECONDS_PER_SECOND
WEEK_HOURS: int = 7 * 24

type AlertCheck = Callable[[PlatformAlertRule, Microseconds], AlertObservation]


class PlatformAlertChecks:
    """
    The platform alert rules' checks (counts, signals, pulses, spend, data
    tasks, `extra_checks` burn rates); a check that fails is skipped, logged.
    """

    def __init__(
        self,
        system_health_repo: SystemHealthRepoContract,
        platform_activity_repo: PlatformActivityRepoContract,
        signal_counter: SignalCounterAdapterContract,
        quality_totals_repo: QualityTotalsRepoContract,
        spend_checks: SpendAlertChecks,
        data_task_checks: DataTaskAlertChecks,
        extra_checks: Mapping[PlatformAlertCode, AlertCheck],
    ) -> None:
        self._health: SystemHealthRepoContract = system_health_repo
        self._activity: PlatformActivityRepoContract = platform_activity_repo
        self._signals: SignalCounterAdapterContract = signal_counter
        self._quality: QualityTotalsRepoContract = quality_totals_repo
        self._checks: Mapping[PlatformAlertCode, AlertCheck] = {
            PlatformAlertCode.DEAD_JOBS: self._dead_jobs,
            PlatformAlertCode.INBOUND_BACKLOG: self._inbound_backlog,
            PlatformAlertCode.OUTBOUND_FAILURES: self._outbound_failures,
            PlatformAlertCode.LLM_ERRORS: self._llm_errors,
            PlatformAlertCode.HANDOFF_SPIKE: self._handoff_spike,
            PlatformAlertCode.TOOL_ERRORS: self._tool_errors,
            PlatformAlertCode.STALE_WORKER: self._stale_worker,
            PlatformAlertCode.OTP_CAP_TRIPS: self._otp_cap_trips,
            PlatformAlertCode.QUALITY_DROP: self._quality_drop,
            PlatformAlertCode.SPEND_SPIKE: spend_checks.spend_spike,
            PlatformAlertCode.SPEND_BUDGET: spend_checks.spend_budget,
            PlatformAlertCode.BACKFILL_STALLED: data_task_checks.backfill_stalled,
            **extra_checks,  # The burn-rate checks (burn_rate_alert_checks.py).
        }

    def run(
        self,
        rules: Mapping[PlatformAlertCode, PlatformAlertRule],
        now: Microseconds,
    ) -> list[AlertObservation]:
        observations: list[AlertObservation] = []
        for code, rule in rules.items():
            try:
                observations.append(self._checks[code](rule, now))
            except ApplicationError as error:
                logger.warning("Platform alert check %s failed: %s", code, error)
        return observations

    def _dead_jobs(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        tallies = self._health.count_dead_jobs_by_name()
        total: int = sum(int(tally.count) for tally in tallies)
        names: str = ", ".join(f"{tally.name} {int(tally.count)}" for tally in tallies)
        detail: str = (
            f"Dead jobs: {total} ({names}). Retry or discard them on the system page."
            if total
            else "No dead jobs."
        )
        return observe(rule, total, detail)

    def _inbound_backlog(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        oldest: QueuedJobDocument | None = self._health.find_oldest_due_job(
            JobLane.INBOUND, now
        )
        if oldest is None:
            return observe(rule, 0, "No customer message waits for a worker.")

        waited: int = max(0, (int(now) - int(oldest.run_at)) // MICROSECONDS_PER_SECOND)
        waiting: int = int(self._health.count_due_jobs(JobLane.INBOUND, now))
        return observe(
            rule,
            waited,
            f"The oldest of {waiting} waiting customer messages has waited "
            f"{describe_duration(waited)}.",
        )

    def _outbound_failures(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        counts: dict[OutboundMessageStatus, int] = {
            tally.status: int(tally.count)
            for tally in self._activity.count_outbound(window_before(rule, now))
        }
        failed: int = counts.get(OutboundMessageStatus.DEAD, 0)
        settled: int = failed + counts.get(OutboundMessageStatus.DELIVERED, 0)
        return observe_rate(
            rule,
            failed,
            settled,
            f"{failed} of {settled} messages queued in the last hour failed for "
            f"good ({describe_percent(failed, settled)}).",
        )

    def _llm_errors(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        calls = self._signals.read(PlatformSignal.LLM_CALL, now)
        errors = self._signals.read(PlatformSignal.LLM_ERROR, now)
        called: int = int(calls.current) + int(calls.previous)
        failed: int = min(called, int(errors.current) + int(errors.previous))
        return observe_rate(
            rule,
            failed,
            called,
            f"{failed} of {called} model calls failed in the last "
            f"{int(rule.window_minutes)}-{2 * int(rule.window_minutes)} minutes "
            f"({describe_percent(failed, called)}).",
        )

    def _handoff_spike(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        hour = window_before(rule, now)
        week = ActivityWindow(
            since=Microseconds(
                int(hour.since) - WEEK_HOURS * 60 * MICROSECONDS_PER_MINUTE
            ),
            until=hour.since,
        )
        last_hour: int = int(self._activity.count_handoffs(hour))
        last_week: int = int(self._activity.count_handoffs(week))
        multiple: int = int(rule.threshold)
        # Above `multiple` times the hourly mean, compared in whole numbers.
        spike_from: int = max(
            int(rule.volume_floor), -(-multiple * last_week // WEEK_HOURS)
        )
        is_spike: bool = (
            last_hour >= int(rule.volume_floor)
            and last_hour * WEEK_HOURS > multiple * last_week
        )
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(last_hour),
            threshold=AlertThreshold(spike_from),
            unit=rule.unit,
            detail=AlertDetailText(
                f"{last_hour} handoffs in the last hour; the week before averaged "
                f"{last_week / WEEK_HOURS:.1f} an hour."
            ),
            is_firing=is_spike,
        )

    def _tool_errors(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        failed: int = int(
            self._activity.count_tool_error_messages(window_before(rule, now))
        )
        return observe(
            rule, failed, f"{failed} replies had a failed tool call in the last hour."
        )

    def _stale_worker(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        window = window_before(rule, now)
        stale = find_stale_workers(self._health.list_pulses_since(window.since), now)
        detail: str = (
            "; ".join(
                f"{pulse.host_name} last beat "
                f"{describe_duration(pulse_age_seconds(pulse, now))} ago"
                for pulse in stale
            )
            if stale
            else "Every worker of the current release beats."
        )
        return observe(rule, len(stale), detail)

    def _otp_cap_trips(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        trips = self._signals.read(PlatformSignal.OTP_CAP_TRIP, now)
        refused: int = int(trips.current) + int(trips.previous)
        return observe(
            rule,
            refused,
            f"{refused} login codes were refused by a platform cap in the last "
            f"{int(rule.window_minutes)}-{2 * int(rule.window_minutes)} minutes.",
        )

    def _quality_drop(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        day = window_before(rule, now)
        recent = self._quality.sum_judged(day)
        earlier = self._quality.sum_judged(
            ActivityWindow(
                since=Microseconds(
                    int(day.since) - WEEK_HOURS * 60 * MICROSECONDS_PER_MINUTE
                ),
                until=day.since,
            )
        )
        dropped: int = int(drop_percent(recent, earlier))
        enough: bool = min(int(recent.sample_count), int(earlier.sample_count)) >= int(
            rule.volume_floor
        )
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(dropped),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(
                f"{int(recent.sample_count)} real conversations scored in the "
                f"last day averaged {describe_average(recent)} of 5; "
                f"{int(earlier.sample_count)} of the 7 days before averaged "
                f"{describe_average(earlier)}."
            ),
            is_firing=enough and dropped > int(rule.threshold),
        )


def observe(rule: PlatformAlertRule, figure: int, detail: str) -> AlertObservation:
    """A figure compared with the rule's own threshold."""

    return AlertObservation(
        code=rule.code,
        figure=AlertFigure(figure),
        threshold=rule.threshold,
        unit=rule.unit,
        detail=AlertDetailText(detail),
        is_firing=figure > int(rule.threshold),
    )


def observe_rate(
    rule: PlatformAlertRule, part: int, whole: int, detail: str
) -> AlertObservation:
    """
    A percentage compared exactly (`part / whole > threshold%`), once the
    window holds the rule's volume floor.
    """

    return AlertObservation(
        code=rule.code,
        figure=AlertFigure(round(part * 100 / whole) if whole else 0),
        threshold=rule.threshold,
        unit=rule.unit,
        detail=AlertDetailText(detail),
        is_firing=(
            whole >= int(rule.volume_floor)
            and whole > 0
            and part * 100 > int(rule.threshold) * whole
        ),
    )


def window_before(rule: PlatformAlertRule, now: Microseconds) -> ActivityWindow:
    """The rule's window that ends now."""

    return ActivityWindow(
        since=Microseconds(
            int(now) - int(rule.window_minutes) * MICROSECONDS_PER_MINUTE
        ),
        until=Microseconds(int(now) + 1),
    )
