"""How the admin system page shows workers, channels, runs and alerts."""

from collections.abc import Mapping, Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import (
    MaintenanceRunOutcome,
    PlatformAlertCode,
    PlatformAlertStatus,
)
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.admin_system import (
    AlertStateView,
    ChannelIssueView,
    MaintenanceRunView,
    WorkerPulseView,
)
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.monitoring.constrained_integers import WorkerPulseAgeSeconds
from app.use_cases.admin.alerts.stale_workers import is_pulse_stale, pulse_age_seconds

MICROSECONDS_PER_HOUR: int = 60 * 60 * 1_000_000
# A resolved alert stays on the page for a day, so the team sees what
# happened overnight.
RESOLVED_ALERTS_SHOWN_FOR: int = 24 * MICROSECONDS_PER_HOUR
SEVERITY_ORDER: tuple[str, ...] = ("sev1", "sev2", "sev3")


def worker_view(pulse: WorkerHeartbeatDocument, now: Microseconds) -> WorkerPulseView:
    return WorkerPulseView(
        worker_id=pulse.id,
        host_name=pulse.host_name,
        release=pulse.release,
        started_at=pulse.started_at,
        beat_at=pulse.beat_at,
        age_seconds=WorkerPulseAgeSeconds(pulse_age_seconds(pulse, now)),
        is_stale=is_pulse_stale(pulse, now),
        failing_jobs=[
            result.job_name
            for result in pulse.periodic_results
            if result.outcome is PeriodicJobOutcome.FAILED
        ],
    )


def channel_issue_view(
    channel: ChannelDocument,
    businesses: Mapping[BusinessId, BusinessDocument],
    now: Microseconds,
) -> ChannelIssueView:
    business: BusinessDocument | None = businesses.get(channel.business_id)
    expires_at: Microseconds | None = channel.credential_expires_at
    return ChannelIssueView(
        channel_id=channel.id,
        business_id=channel.business_id,
        business_name=None if business is None else business.name,
        kind=channel.kind,
        last_error=channel.last_error,
        last_error_at=channel.last_error_at,
        credential_expires_at=expires_at,
        is_expired=expires_at is not None and int(expires_at) <= int(now),
    )


def run_view(run: MaintenanceRunDocument | None) -> MaintenanceRunView | None:
    if run is None:
        return None

    return MaintenanceRunView(
        kind=run.kind,
        outcome=run.outcome,
        started_at=run.started_at,
        finished_at=run.finished_at,
        archive_size=run.archive_size,
        row_count=run.row_count,
        error=run.error,
        release=run.release,
    )


def is_backup_overdue(
    last_backup: MaintenanceRunDocument | None,
    max_age: BackupFreshnessHours,
    now: Microseconds,
) -> bool:
    """No backup recorded, the last one failed, or it is older than allowed."""

    if (
        last_backup is None
        or last_backup.outcome is not MaintenanceRunOutcome.SUCCEEDED
    ):
        return True

    return (
        int(now) - int(last_backup.finished_at) > int(max_age) * MICROSECONDS_PER_HOUR
    )


def alert_views(
    states: Sequence[PlatformAlertStateDocument],
    rules: Mapping[PlatformAlertCode, PlatformAlertRule],
    now: Microseconds,
) -> list[AlertStateView]:
    """Firing alerts first (the worst first), then those resolved within a day."""

    shown: list[AlertStateView] = []
    for state in states:
        rule: PlatformAlertRule | None = rules.get(state.code)
        is_recent: bool = (
            state.resolved_at is not None
            and int(now) - int(state.resolved_at) <= RESOLVED_ALERTS_SHOWN_FOR
        )
        if rule is None or (
            state.status is PlatformAlertStatus.RESOLVED and not is_recent
        ):
            continue

        shown.append(
            AlertStateView(
                code=state.code,
                status=state.status,
                severity=rule.severity,
                summary=rule.summary,
                figure=state.figure,
                threshold=state.threshold,
                unit=state.unit,
                detail=state.detail,
                fired_at=state.fired_at,
                notified_at=state.notified_at,
                notification_count=state.notification_count,
                resolved_at=state.resolved_at,
                runbook=rule.runbook,
            )
        )

    return sorted(
        shown,
        key=lambda view: (
            view.status is not PlatformAlertStatus.FIRING,
            SEVERITY_ORDER.index(view.severity.value),
            -int(view.fired_at),
        ),
    )
