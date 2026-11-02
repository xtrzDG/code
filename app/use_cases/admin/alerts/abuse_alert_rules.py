"""
The abuse alert rules (ABUSE-04, VOICE-09), the code's copy of
ops/alerts/{booking_spike,cancellation_spike,whatsapp_quality}.yaml. Each
fires on any counted event in the shared signal windows: a business past
40 new bookings or 15 cancellations in an hour (counted where the change
is announced, `BookingSurgeObserverFacilitator`), or a warning of Meta
about a WhatsApp number or template (counted by the WhatsApp webhook,
`report_quality_warnings`).
"""

from app.schemas.constants.incidents import IncidentSeverity
from app.schemas.constants.monitoring import AlertUnit, PlatformAlertCode
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.schemas.typings.monitoring.constrained_integers import (
    AlertThreshold,
    AlertVolumeFloor,
)
from app.schemas.typings.monitoring.constrained_strings import AlertRunbookPath
from app.schemas.typings.monitoring.strings import AlertRuleSummary
from app.utilities.monitoring.signal_windows import SIGNAL_WINDOW_MINUTES

BOOKING_RUNBOOK: AlertRunbookPath = AlertRunbookPath(
    "docs/operations/runbooks/booking-abuse.md"
)
WHATSAPP_RUNBOOK: AlertRunbookPath = AlertRunbookPath(
    "docs/operations/runbooks/whatsapp-quality.md"
)
ANY_EVENT: AlertThreshold = AlertThreshold(0)
NO_FLOOR: AlertVolumeFloor = AlertVolumeFloor(0)

ABUSE_ALERT_RULES: tuple[PlatformAlertRule, ...] = (
    PlatformAlertRule(
        code=PlatformAlertCode.BOOKING_SPIKE,
        severity=IncidentSeverity.SEV3,
        summary=AlertRuleSummary(
            "A business got more than 40 new bookings in an hour (fake "
            "bookings holding every slot)."
        ),
        threshold=ANY_EVENT,
        unit=AlertUnit.COUNT,
        window_minutes=SIGNAL_WINDOW_MINUTES,
        volume_floor=NO_FLOOR,
        runbook=BOOKING_RUNBOOK,
    ),
    PlatformAlertRule(
        code=PlatformAlertCode.CANCELLATION_SPIKE,
        severity=IncidentSeverity.SEV3,
        summary=AlertRuleSummary(
            "A business had more than 15 bookings cancelled in an hour (a "
            "mass cancellation)."
        ),
        threshold=ANY_EVENT,
        unit=AlertUnit.COUNT,
        window_minutes=SIGNAL_WINDOW_MINUTES,
        volume_floor=NO_FLOOR,
        runbook=BOOKING_RUNBOOK,
    ),
    PlatformAlertRule(
        code=PlatformAlertCode.WHATSAPP_QUALITY,
        severity=IncidentSeverity.SEV2,
        summary=AlertRuleSummary(
            "Meta flagged or downgraded a WhatsApp number, lowered or paused a "
            "template, or moved one into the marketing category."
        ),
        threshold=ANY_EVENT,
        unit=AlertUnit.COUNT,
        window_minutes=SIGNAL_WINDOW_MINUTES,
        volume_floor=NO_FLOOR,
        runbook=WHATSAPP_RUNBOOK,
    ),
)
