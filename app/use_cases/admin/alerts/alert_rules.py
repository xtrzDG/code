"""
The platform alert rules: the code's copy of ops/alerts/*.yaml (a test
keeps both the same, so a threshold is changed in one reviewed place and
the code follows). A rule fires when its figure is above its threshold.
"""

from collections.abc import Mapping

from app.schemas.constants.incidents import IncidentSeverity
from app.schemas.constants.monitoring import AlertUnit, PlatformAlertCode
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.schemas.typings.monitoring.constrained_integers import (
    AlertThreshold,
    AlertVolumeFloor,
    AlertWindowMinutes,
)
from app.schemas.typings.monitoring.constrained_strings import AlertRunbookPath
from app.schemas.typings.monitoring.strings import AlertRuleSummary
from app.utilities.monitoring.signal_windows import SIGNAL_WINDOW_MINUTES

RUNBOOKS: str = "docs/operations/runbooks/"
CHECK_INTERVAL_MINUTES: AlertWindowMinutes = AlertWindowMinutes(5)
HOUR_MINUTES: AlertWindowMinutes = AlertWindowMinutes(60)


def _rule(
    code: PlatformAlertCode,
    severity: IncidentSeverity,
    summary: str,
    threshold: int,
    unit: AlertUnit,
    window_minutes: AlertWindowMinutes,
    runbook: str,
    volume_floor: int = 0,
) -> PlatformAlertRule:
    return PlatformAlertRule(
        code=code,
        severity=severity,
        summary=AlertRuleSummary(summary),
        threshold=AlertThreshold(threshold),
        unit=unit,
        window_minutes=window_minutes,
        volume_floor=AlertVolumeFloor(volume_floor),
        runbook=AlertRunbookPath(f"{RUNBOOKS}{runbook}"),
    )


PLATFORM_ALERT_RULES: Mapping[PlatformAlertCode, PlatformAlertRule] = {
    rule.code: rule
    for rule in (
        _rule(
            PlatformAlertCode.DEAD_JOBS,
            IncidentSeverity.SEV2,
            "Background jobs ran out of attempts and wait in the dead letters.",
            0,
            AlertUnit.COUNT,
            CHECK_INTERVAL_MINUTES,
            "stuck-worker.md",
        ),
        _rule(
            PlatformAlertCode.INBOUND_BACKLOG,
            IncidentSeverity.SEV2,
            "The oldest customer message waits for a worker too long.",
            120,
            AlertUnit.SECONDS,
            CHECK_INTERVAL_MINUTES,
            "stuck-worker.md",
        ),
        _rule(
            PlatformAlertCode.OUTBOUND_FAILURES,
            IncidentSeverity.SEV2,
            "Replies and staff notifications fail for good.",
            10,
            AlertUnit.PERCENT,
            HOUR_MINUTES,
            "delivery-failures.md",
            volume_floor=20,
        ),
        _rule(
            PlatformAlertCode.LLM_ERRORS,
            IncidentSeverity.SEV1,
            "Language model calls fail.",
            5,
            AlertUnit.PERCENT,
            SIGNAL_WINDOW_MINUTES,
            "llm-outage.md",
            volume_floor=20,
        ),
        _rule(
            PlatformAlertCode.HANDOFF_SPIKE,
            IncidentSeverity.SEV2,
            "Far more conversations go to people than in an hour of the last week.",
            3,
            AlertUnit.RATIO,
            HOUR_MINUTES,
            "assistant-quality.md",
            volume_floor=5,
        ),
        _rule(
            PlatformAlertCode.TOOL_ERRORS,
            IncidentSeverity.SEV3,
            "The assistant's tools (bookings, prices, availability) fail.",
            5,
            AlertUnit.COUNT,
            HOUR_MINUTES,
            "assistant-quality.md",
        ),
        _rule(
            PlatformAlertCode.STALE_WORKER,
            IncidentSeverity.SEV2,
            "A worker of the current release stopped writing its pulse.",
            0,
            AlertUnit.COUNT,
            # Pulses are kept a day: a hung worker pages until it is replaced.
            AlertWindowMinutes(24 * 60),
            "stuck-worker.md",
        ),
        _rule(
            PlatformAlertCode.OTP_CAP_TRIPS,
            IncidentSeverity.SEV2,
            "A platform cap refused login codes (SMS pumping or a login flood).",
            0,
            AlertUnit.COUNT,
            SIGNAL_WINDOW_MINUTES,
            "sms-pumping.md",
        ),
    )
}
