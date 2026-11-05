"""
The platform health alert rules (LOG-04, LOG-05), the code's copy of
ops/alerts/{webhook_signature_failures,storage_errors,api_latency,
backup_failed,tenant_sms_volume,otp_conversion,
tenant_payment_declines}.yaml. Each fires when its figure is above its
threshold; the counted signals are written by the processes that see the
events (platform_health_alert_checks.py).
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
from app.utilities.monitoring.signal_windows import SIGNAL_WINDOW_MINUTES

RUNBOOKS: str = "docs/operations/runbooks/"
HOUR: AlertWindowMinutes = AlertWindowMinutes(60)
# A daily backup may start up to two hours late before it counts as missed.
BACKUP_FRESHNESS: AlertWindowMinutes = AlertWindowMinutes(26 * 60)
NO_FLOOR: AlertVolumeFloor = AlertVolumeFloor(0)
# The API requests a latency share needs before it means anything.
API_LATENCY_FLOOR: AlertVolumeFloor = AlertVolumeFloor(200)
# The settled login codes an hour's conversion needs.
OTP_CONVERSION_FLOOR: AlertVolumeFloor = AlertVolumeFloor(20)


def _rule(
    code: PlatformAlertCode,
    severity: IncidentSeverity,
    summary: str,
    threshold: int,
    unit: AlertUnit,
    window_minutes: AlertWindowMinutes,
    runbook: str,
    volume_floor: AlertVolumeFloor = NO_FLOOR,
) -> PlatformAlertRule:
    return PlatformAlertRule(
        code=code,
        severity=severity,
        summary=AlertRuleSummary(summary),
        threshold=AlertThreshold(threshold),
        unit=unit,
        window_minutes=window_minutes,
        volume_floor=volume_floor,
        runbook=AlertRunbookPath(f"{RUNBOOKS}{runbook}"),
    )


PLATFORM_HEALTH_ALERT_RULES: tuple[PlatformAlertRule, ...] = (
    _rule(
        PlatformAlertCode.WEBHOOK_SIGNATURE_FAILURES,
        IncidentSeverity.SEV2,
        "More than 30 webhook deliveries were refused as unsigned, badly "
        "signed or stale in 15 to 30 minutes.",
        30,
        AlertUnit.COUNT,
        SIGNAL_WINDOW_MINUTES,
        "webhook-signature-failures.md",
    ),
    _rule(
        PlatformAlertCode.STORAGE_ERRORS,
        IncidentSeverity.SEV1,
        "More than 5 requests or jobs failed on the database or the object "
        "storage in 15 to 30 minutes.",
        5,
        AlertUnit.COUNT,
        SIGNAL_WINDOW_MINUTES,
        "storage-errors.md",
    ),
    _rule(
        PlatformAlertCode.API_LATENCY,
        IncidentSeverity.SEV2,
        "More than 5 % of API requests took longer than 2 s in the last 30 minutes.",
        5,
        AlertUnit.PERCENT,
        AlertWindowMinutes(2 * int(SIGNAL_WINDOW_MINUTES)),
        "api-latency.md",
        API_LATENCY_FLOOR,
    ),
    _rule(
        PlatformAlertCode.BACKUP_FAILED,
        IncidentSeverity.SEV2,
        "The last off-site database backup failed, or none succeeded for 26 hours.",
        0,
        AlertUnit.COUNT,
        BACKUP_FRESHNESS,
        "backup-failed.md",
    ),
    _rule(
        PlatformAlertCode.TENANT_SMS_VOLUME,
        IncidentSeverity.SEV2,
        "A business sent more than 60 SMS in an hour, or its SMS were "
        "refused past 200 an hour.",
        0,
        AlertUnit.COUNT,
        SIGNAL_WINDOW_MINUTES,
        "tenant-sms-volume.md",
    ),
    _rule(
        PlatformAlertCode.OTP_CONVERSION,
        IncidentSeverity.SEV2,
        "More than 70 % of the login codes sent in the last hour were never used.",
        70,
        AlertUnit.PERCENT,
        HOUR,
        "tenant-sms-volume.md",
        OTP_CONVERSION_FLOOR,
    ),
    _rule(
        PlatformAlertCode.TENANT_PAYMENT_DECLINES,
        IncidentSeverity.SEV2,
        "The payments of a business were declined 5 times within two hours "
        "(card testing); from 10 its new payment pages are refused.",
        0,
        AlertUnit.COUNT,
        SIGNAL_WINDOW_MINUTES,
        "tenant-payment-declines.md",
    ),
)
