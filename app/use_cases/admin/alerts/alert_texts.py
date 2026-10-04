"""
The English texts of the platform alerts: the detail line of each check
and the message the team gets. The team works in English (the runbooks
are English); no text names a person, a customer or a message's content.
"""

from datetime import UTC, datetime

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import AlertNoticeKind
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

MICROSECONDS_PER_SECOND: int = 1_000_000
SYSTEM_PAGE_PATH: str = "/admin/system"
NOTICE_HEADINGS: dict[AlertNoticeKind, str] = {
    AlertNoticeKind.FIRING: "FIRING",
    AlertNoticeKind.STILL_FIRING: "STILL FIRING",
    AlertNoticeKind.RESOLVED: "RESOLVED",
}
ALERT_TITLES: dict[str, str] = {
    "dead_jobs": "Dead jobs",
    "inbound_backlog": "Customer messages wait",
    "outbound_failures": "Deliveries fail",
    "llm_errors": "Model calls fail",
    "handoff_spike": "Handoff spike",
    "tool_errors": "Tool errors",
    "stale_worker": "Worker stopped",
    "otp_cap_trips": "Login codes refused",
}


def describe_duration(seconds: int) -> str:
    """A short English duration: "45 s", "3 min 20 s", "2 h 5 min"."""

    if seconds < 60:
        return f"{seconds} s"

    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {rest} s" if rest else f"{minutes} min"

    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min" if minutes else f"{hours} h"


def describe_percent(part: int, whole: int) -> str:
    """`part` of `whole` as a whole percentage ("17%"); "0%" of nothing."""

    return f"{round(part * 100 / whole) if whole else 0}%"


def describe_time(moment: Microseconds) -> str:
    """A moment in UTC to the minute ("2026-10-04 12:05 UTC")."""

    seconds: float = int(moment) / MICROSECONDS_PER_SECOND
    return datetime.fromtimestamp(seconds, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


def compose_alert_message(
    rule: PlatformAlertRule,
    state: PlatformAlertStateDocument,
    notice: AlertNoticeKind,
    cabinet_base_url: CabinetBaseUrl | None,
) -> PlatformAlertMessage:
    """
    The message of one notice: severity, state and title on the first line
    (the e-mail subject), then what the rule watches, what the check found,
    since when, the runbook and the system page.
    """

    title: str = ALERT_TITLES.get(state.code.value, state.code.value)
    lines: list[str] = [
        f"[{rule.severity.value.upper()}] {NOTICE_HEADINGS[notice]}: {title}",
        str(rule.summary),
        str(state.detail),
        f"Since {describe_time(state.fired_at)}",
    ]
    if notice is AlertNoticeKind.RESOLVED and state.resolved_at is not None:
        lines[-1] = (
            f"From {describe_time(state.fired_at)} to "
            f"{describe_time(state.resolved_at)}"
        )

    lines.append(f"Runbook: {rule.runbook}")
    if cabinet_base_url is not None:
        lines.append(
            f"System page: {str(cabinet_base_url).rstrip('/')}{SYSTEM_PAGE_PATH}"
        )

    return PlatformAlertMessage("\n".join(lines))
