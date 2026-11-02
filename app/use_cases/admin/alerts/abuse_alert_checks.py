"""
The checks of the abuse alert rules (`abuse_alert_rules.py`): the events
of their signals in the window still filling and the one before. The
detail never names a customer: the warning lines of the log name the
business (bookings) or the template and number (WhatsApp).
"""

from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.monitoring import SignalCounterAdapterContract
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.dto.platform_alerts import (
    AlertObservation,
    PlatformAlertRule,
    SignalTally,
)
from app.use_cases.admin.alerts.alert_checks import AlertCheck, observe


class AbuseAlertChecks:
    """The three checks, by alert code (`checks`)."""

    def __init__(self, signal_counter: SignalCounterAdapterContract) -> None:
        self._signals: SignalCounterAdapterContract = signal_counter

    def checks(self) -> Mapping[PlatformAlertCode, AlertCheck]:
        return {
            PlatformAlertCode.BOOKING_SPIKE: self.booking_spike,
            PlatformAlertCode.CANCELLATION_SPIKE: self.cancellation_spike,
            PlatformAlertCode.WHATSAPP_QUALITY: self.whatsapp_quality,
        }

    def booking_spike(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        over: int = self._recent(PlatformSignal.BOOKING_SURGE, now)
        return observe(
            rule,
            over,
            f"{over} bookings past a business's hourly cap in the last "
            f"{minutes(rule)} minutes; the log names the business.",
        )

    def cancellation_spike(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        over: int = self._recent(PlatformSignal.CANCELLATION_SURGE, now)
        return observe(
            rule,
            over,
            f"{over} cancellations past a business's hourly cap in the last "
            f"{minutes(rule)} minutes; the log names the business.",
        )

    def whatsapp_quality(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        warnings: int = self._recent(PlatformSignal.WHATSAPP_QUALITY_DROP, now)
        return observe(
            rule,
            warnings,
            f"{warnings} quality warnings from Meta in the last {minutes(rule)} "
            "minutes; the log names the number or the template.",
        )

    def _recent(self, signal: PlatformSignal, now: Microseconds) -> int:
        tally: SignalTally = self._signals.read(signal, now)
        return int(tally.current) + int(tally.previous)


def minutes(rule: PlatformAlertRule) -> str:
    """The span the two signal windows cover: "15-30"."""

    window: int = int(rule.window_minutes)
    return f"{window}-{2 * window}"
