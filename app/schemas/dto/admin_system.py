"""
GET /v1/admin/system: the whole platform on one page for the platform
admin. Every figure comes from an indexed count or a short indexed list,
never from reading a whole collection.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.incidents import IncidentSeverity
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.monitoring import (
    AlertUnit,
    MaintenanceRunKind,
    MaintenanceRunOutcome,
    PlatformAlertCode,
    PlatformAlertStatus,
)
from app.schemas.typings.backups.constrained_integers import (
    BackupArchiveSize,
    TableRowCount,
)
from app.schemas.typings.backups.constrained_strings import DatabaseTableName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import ChannelErrorSummary
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.monitoring.booleans import (
    IsBackupOverdue,
    IsCredentialExpired,
    IsWorkerPulseStale,
)
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
    ChannelIssueCount,
    CollectionRowEstimate,
    LaneJobCount,
    NotificationCount,
    StorageByteSize,
    WaitSeconds,
    WorkerPulseAgeSeconds,
)
from app.schemas.typings.monitoring.constrained_strings import AlertRunbookPath
from app.schemas.typings.monitoring.strings import (
    AlertDetailText,
    AlertRuleSummary,
    MaintenanceErrorText,
)
from app.schemas.typings.platform.constrained_strings import (
    JobName,
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.platform.prefixed_id import WorkerInstanceId
from app.schemas.typings.users.prefixed_id import UserId


class AdminSystemQuery(ImmutableDTO):
    user_id: UserId


class WorkerPulseView(ImmutableDTO):
    """
    One worker process that beat within the last day: its build, since when
    it runs, how old its last pulse is (stale after five minutes) and the
    periodic jobs whose last run in it failed.
    """

    worker_id: WorkerInstanceId
    host_name: WorkerHostName
    release: ReleaseVersion | None = None
    started_at: Microseconds
    beat_at: Microseconds
    age_seconds: WorkerPulseAgeSeconds
    is_stale: IsWorkerPulseStale
    failing_jobs: list[JobName]


class LaneView(ImmutableDTO):
    """
    One lane of the job queue: jobs due and waiting for a worker, waiting
    for a later time (retries with backoff, scheduled work), running, and
    dead; how long the oldest due job has waited (None: nothing waits).
    """

    lane: JobLane
    waiting: LaneJobCount
    scheduled: LaneJobCount
    running: LaneJobCount
    dead: LaneJobCount
    oldest_wait_seconds: WaitSeconds | None = None


class DeadJobTally(ImmutableDTO):
    """How many dead letters one job name has."""

    name: JobName
    count: LaneJobCount


class ChannelIssueView(ImmutableDTO):
    """
    A connected channel that needs the team: in ERROR (the platform refused
    its credential or deliveries fail), or a Meta token that runs out soon
    (`credential_expires_at`) or already did.
    """

    channel_id: ChannelId
    business_id: BusinessId
    business_name: BusinessName | None = None
    kind: ChannelKind
    last_error: ChannelErrorSummary | None = None
    last_error_at: Microseconds | None = None
    credential_expires_at: Microseconds | None = None
    is_expired: IsCredentialExpired = False


class TableSizeView(ImmutableDTO):
    """One table of the database: its disk space with indexes, its rows (estimated)."""

    table: DatabaseTableName
    total_bytes: StorageByteSize
    row_estimate: CollectionRowEstimate


class MaintenanceRunView(ImmutableDTO):
    """The last backup or restore drill and how it ended."""

    kind: MaintenanceRunKind
    outcome: MaintenanceRunOutcome
    started_at: Microseconds
    finished_at: Microseconds
    archive_size: BackupArchiveSize | None = None
    row_count: TableRowCount | None = None
    error: MaintenanceErrorText | None = None
    release: ReleaseVersion | None = None


class AlertStateView(ImmutableDTO):
    """A platform alert that fires now, or whose last episode ended within a day."""

    code: PlatformAlertCode
    status: PlatformAlertStatus
    severity: IncidentSeverity
    summary: AlertRuleSummary
    figure: AlertFigure
    threshold: AlertThreshold
    unit: AlertUnit
    detail: AlertDetailText
    fired_at: Microseconds
    notified_at: Microseconds | None = None
    notification_count: NotificationCount
    resolved_at: Microseconds | None = None
    runbook: AlertRunbookPath


class AdminSystemView(ImmutableDTO):
    """
    The platform at `checked_at`: workers, queue lanes and dead letters,
    channels that need the team, database size by table (None without
    Postgres), the last backup and restore drill, and the platform alerts.
    """

    checked_at: Microseconds
    workers: list[WorkerPulseView]
    lanes: list[LaneView]
    dead_jobs: list[DeadJobTally]
    channels_in_error: list[ChannelIssueView]
    channels_in_error_count: ChannelIssueCount
    expiring_credentials: list[ChannelIssueView]
    database_bytes: StorageByteSize | None = None
    tables: list[TableSizeView]
    last_backup: MaintenanceRunView | None = None
    last_restore_drill: MaintenanceRunView | None = None
    is_backup_overdue: IsBackupOverdue
    alerts: list[AlertStateView]
