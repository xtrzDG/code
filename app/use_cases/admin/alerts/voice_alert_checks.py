"""
The voice_health alert's check: the phone assistant's platform (ElevenLabs)
fails its API calls, or its finished-call reports stopped while every day
of the week before had calls at this time of day.
"""

from typed_time_provider import Microseconds

from app.contracts.monitoring import (
    SignalCounterAdapterContract,
    VoiceActivityRepoContract,
)
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.typings.monitoring.constrained_integers import AlertFigure
from app.schemas.typings.monitoring.strings import AlertDetailText

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000
DAY_MINUTES: int = 24 * 60
# How long the reports may pause before silence means something: calls
# come in bursts, three quiet hours in a busy slot do not.
SILENCE_WINDOW_MINUTES: int = 3 * 60
PATTERN_DAYS: int = 7


class VoiceHealthAlertCheck:
    """
    Fires when either is true:

    - more than `threshold` calls of the voice platform's API failed in the
      last 15 to 30 minutes (the shared signals `voice_api_call` and
      `voice_api_error`: setting up agents, playing, archiving and
      deleting recordings, erasures);
    - no finished-call report arrived in the last SILENCE_WINDOW_MINUTES,
      while each of the PATTERN_DAYS days before had at least
      `volume_floor` reports in the same hours (the platform's post-call
      webhook stopped, or calls stopped reaching the agents). Asking every
      one of those days keeps a quiet weekday or a closed Sunday from
      paging.

    The figure is the failed API calls; the detail tells both sides.
    """

    def __init__(
        self,
        signal_counter: SignalCounterAdapterContract,
        voice_activity_repo: VoiceActivityRepoContract,
    ) -> None:
        self._signals: SignalCounterAdapterContract = signal_counter
        self._activity: VoiceActivityRepoContract = voice_activity_repo

    def check(self, rule: PlatformAlertRule, now: Microseconds) -> AlertObservation:
        calls = self._signals.read(PlatformSignal.VOICE_API_CALL, now)
        errors = self._signals.read(PlatformSignal.VOICE_API_ERROR, now)
        called: int = int(calls.current) + int(calls.previous)
        failed: int = min(called, int(errors.current) + int(errors.previous))
        received: int = self._reports(now, days_ago=0)
        fewest_before: int = min(
            self._reports(now, days_ago=day) for day in range(1, PATTERN_DAYS + 1)
        )
        is_silent: bool = received == 0 and fewest_before >= max(
            1, int(rule.volume_floor)
        )
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(failed),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(
                f"{failed} of {called} voice platform API calls failed in the "
                f"last {int(rule.window_minutes)}-{2 * int(rule.window_minutes)} "
                f"minutes. {received} finished-call reports arrived in the last "
                f"{SILENCE_WINDOW_MINUTES // 60} hours; each of the "
                f"{PATTERN_DAYS} days before had at least {fewest_before} in "
                "these hours."
            ),
            is_firing=failed > int(rule.threshold) or is_silent,
        )

    def _reports(self, now: Microseconds, days_ago: int) -> int:
        until: int = int(now) + 1 - days_ago * DAY_MINUTES * MICROSECONDS_PER_MINUTE
        since: int = until - SILENCE_WINDOW_MINUTES * MICROSECONDS_PER_MINUTE
        return int(
            self._activity.count_post_call_reports(
                ActivityWindow(since=Microseconds(since), until=Microseconds(until))
            )
        )
