"""
The multi-window burn-rate rules of the SLOs (docs/operations/slo.md),
the code's copy of ops/alerts/*_budget_*_burn.yaml: a rule fires when both
its long and its short window spend the error budget faster than its
threshold, in percent of the pace that spends it in exactly 28 days
(1440: 14.4 times, the whole month's budget in about two days).
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

RUNBOOK: AlertRunbookPath = AlertRunbookPath(
    "docs/operations/runbooks/error-budget-burn.md"
)
FAST_BURN_PERCENT: AlertThreshold = AlertThreshold(1440)
SLOW_BURN_PERCENT: AlertThreshold = AlertThreshold(600)
# Customer messages and API requests a long window needs before its rate
# means anything (one late answer of three is not an outage).
ANSWER_FLOOR: AlertVolumeFloor = AlertVolumeFloor(20)
API_FLOOR: AlertVolumeFloor = AlertVolumeFloor(100)


def _burn_rule(
    code: PlatformAlertCode,
    is_fast: bool,
    summary: str,
    volume_floor: AlertVolumeFloor,
) -> PlatformAlertRule:
    return PlatformAlertRule(
        code=code,
        severity=IncidentSeverity.SEV1 if is_fast else IncidentSeverity.SEV2,
        summary=AlertRuleSummary(summary),
        threshold=FAST_BURN_PERCENT if is_fast else SLOW_BURN_PERCENT,
        unit=AlertUnit.PERCENT,
        window_minutes=AlertWindowMinutes(60 if is_fast else 360),
        short_window_minutes=AlertWindowMinutes(5 if is_fast else 30),
        volume_floor=volume_floor,
        runbook=RUNBOOK,
    )


BURN_RATE_RULES: tuple[PlatformAlertRule, ...] = (
    _burn_rule(
        PlatformAlertCode.ANSWER_BUDGET_FAST_BURN,
        True,
        "Customer messages miss the 60 s answer at 14.4 times the pace the "
        "monthly error budget allows (1 h and 5 min).",
        ANSWER_FLOOR,
    ),
    _burn_rule(
        PlatformAlertCode.ANSWER_BUDGET_SLOW_BURN,
        False,
        "Customer messages miss the 60 s answer at 6 times the pace the "
        "monthly error budget allows (6 h and 30 min).",
        ANSWER_FLOOR,
    ),
    _burn_rule(
        PlatformAlertCode.API_BUDGET_FAST_BURN,
        True,
        "API requests fail with a server error at 14.4 times the pace the "
        "monthly error budget allows (1 h and 5 min).",
        API_FLOOR,
    ),
    _burn_rule(
        PlatformAlertCode.API_BUDGET_SLOW_BURN,
        False,
        "API requests fail with a server error at 6 times the pace the "
        "monthly error budget allows (6 h and 30 min).",
        API_FLOOR,
    ),
)
