"""
The audit log's alert rules (R13-AUDIT-TRAIL, migration 1193), the code's
copy of ops/alerts/{bulk_personal_data,tenant_hopping,
failed_sign_in_checks,audit_chain_broken}.yaml. Each fires when its figure
is above its threshold.
"""

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

ANOMALY_RUNBOOK: AlertRunbookPath = AlertRunbookPath(
    "docs/operations/runbooks/audit-anomaly.md"
)
CHAIN_RUNBOOK: AlertRunbookPath = AlertRunbookPath(
    "docs/operations/runbooks/audit-chain-broken.md"
)
HOUR: AlertWindowMinutes = AlertWindowMinutes(60)
DAY: AlertWindowMinutes = AlertWindowMinutes(24 * 60)
NO_FLOOR: AlertVolumeFloor = AlertVolumeFloor(0)

AUDIT_ALERT_RULES: tuple[PlatformAlertRule, ...] = (
    PlatformAlertRule(
        code=PlatformAlertCode.BULK_PERSONAL_DATA,
        severity=IncidentSeverity.SEV2,
        summary=AlertRuleSummary(
            "One business exported or erased personal data more than 20 "
            "times in an hour."
        ),
        threshold=AlertThreshold(20),
        unit=AlertUnit.COUNT,
        window_minutes=HOUR,
        volume_floor=NO_FLOOR,
        runbook=ANOMALY_RUNBOOK,
    ),
    PlatformAlertRule(
        code=PlatformAlertCode.TENANT_HOPPING,
        severity=IncidentSeverity.SEV2,
        summary=AlertRuleSummary(
            "One platform admin entered or changed more than 10 clients' "
            "accounts in an hour."
        ),
        threshold=AlertThreshold(10),
        unit=AlertUnit.COUNT,
        window_minutes=HOUR,
        volume_floor=NO_FLOOR,
        runbook=ANOMALY_RUNBOOK,
    ),
    PlatformAlertRule(
        code=PlatformAlertCode.FAILED_SIGN_IN_CHECKS,
        severity=IncidentSeverity.SEV2,
        summary=AlertRuleSummary(
            "More than 50 wrong sign-in codes in an hour for one phone, "
            "e-mail address or person."
        ),
        threshold=AlertThreshold(50),
        unit=AlertUnit.COUNT,
        window_minutes=HOUR,
        volume_floor=NO_FLOOR,
        runbook=ANOMALY_RUNBOOK,
    ),
    PlatformAlertRule(
        code=PlatformAlertCode.AUDIT_CHAIN_BROKEN,
        severity=IncidentSeverity.SEV1,
        summary=AlertRuleSummary(
            "The daily check found an audit log hash chain broken: an entry "
            "was changed, removed or put in."
        ),
        threshold=AlertThreshold(0),
        unit=AlertUnit.COUNT,
        window_minutes=DAY,
        volume_floor=NO_FLOOR,
        runbook=CHAIN_RUNBOOK,
    ),
)
