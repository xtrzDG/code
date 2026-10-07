import logging
from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import (
    DatabaseSizeAdapterContract,
    MaintenanceRunRepoContract,
    PlatformAlertStateRepoContract,
    SystemHealthRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.monitoring import MaintenanceRunKind, PlatformAlertCode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_system import AdminSystemQuery, AdminSystemView, LaneView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.schemas.dto.platform_health import DatabaseSize, JobStateTally
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.monitoring.constrained_integers import (
    ChannelIssueCount,
    LaneJobCount,
    WaitSeconds,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.admin.system.system_views import (
    alert_views,
    channel_issue_view,
    is_backup_overdue,
    run_view,
    worker_view,
)

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
DAY_MICROSECONDS: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND
# Meta tokens shown when they run out within this long (or already did).
CREDENTIAL_NOTICE_MICROSECONDS: int = 14 * DAY_MICROSECONDS
CHANNELS_SHOWN: DocumentQueryLimit = DocumentQueryLimit(20)


class GetAdminSystemUseCase(UseCaseContract[AdminSystemQuery, AdminSystemView]):
    """
    GET /v1/admin/system: the whole platform on one page for a platform
    admin. Worker pulses of the last day, each lane's waiting, scheduled,
    running and dead jobs with the oldest wait, dead letters by job name,
    channels in ERROR and Meta tokens running out within 14 days, the
    database's size by table, the last backup and restore drill, and the
    platform alerts that fire or resolved within a day.

    Every figure is an indexed count, a short indexed list or the system
    catalog (docs/operations/capacity.md); the database size is left out
    when it cannot be read.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        system_health_repo: SystemHealthRepoContract,
        maintenance_run_repo: MaintenanceRunRepoContract,
        alert_state_repo: PlatformAlertStateRepoContract,
        database_size: DatabaseSizeAdapterContract,
        backup_max_age: BackupFreshnessHours,
        wall_clock: WallClock[Microseconds],
        rules: Mapping[PlatformAlertCode, PlatformAlertRule] = PLATFORM_ALERT_RULES,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._health: SystemHealthRepoContract = system_health_repo
        self._runs: MaintenanceRunRepoContract = maintenance_run_repo
        self._alerts: PlatformAlertStateRepoContract = alert_state_repo
        self._database_size: DatabaseSizeAdapterContract = database_size
        self._backup_max_age: BackupFreshnessHours = backup_max_age
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rules: Mapping[PlatformAlertCode, PlatformAlertRule] = rules

    def run(self, input_data: AdminSystemQuery) -> AdminSystemView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        in_error: list[ChannelDocument] = self._health.list_channels_in_error(
            CHANNELS_SHOWN
        )
        expiring: list[ChannelDocument] = self._health.list_credentials_expiring_before(
            Microseconds(int(now) + CREDENTIAL_NOTICE_MICROSECONDS), CHANNELS_SHOWN
        )
        businesses: dict[BusinessId, BusinessDocument] = {
            business.id: business
            for business in self._health.get_businesses(
                sorted({channel.business_id for channel in [*in_error, *expiring]})
            )
        }
        database: DatabaseSize | None = self._measure_database()
        last_backup: MaintenanceRunDocument | None = self._runs.find_latest(
            MaintenanceRunKind.BACKUP
        )
        pulses = self._health.list_pulses_since(
            Microseconds(int(now) - DAY_MICROSECONDS)
        )
        return AdminSystemView(
            checked_at=now,
            workers=[worker_view(pulse, now) for pulse in pulses],
            lanes=self._lanes(now),
            dead_jobs=self._health.count_dead_jobs_by_name(),
            channels_in_error=[
                channel_issue_view(channel, businesses, now) for channel in in_error
            ],
            channels_in_error_count=ChannelIssueCount(
                int(self._health.count_channels_in_error())
            ),
            expiring_credentials=[
                channel_issue_view(channel, businesses, now) for channel in expiring
            ],
            database_bytes=None if database is None else database.total_bytes,
            tables=[] if database is None else database.tables,
            last_backup=run_view(last_backup),
            last_restore_drill=run_view(
                self._runs.find_latest(MaintenanceRunKind.RESTORE_DRILL)
            ),
            is_backup_overdue=is_backup_overdue(last_backup, self._backup_max_age, now),
            alerts=alert_views(
                self._alerts.get_many(list(self._rules)), self._rules, now
            ),
        )

    def _lanes(self, now: Microseconds) -> list[LaneView]:
        tallies: list[JobStateTally] = self._health.count_open_jobs()

        def count(lane: JobLane, status: QueuedJobStatus) -> int:
            return sum(
                int(tally.count)
                for tally in tallies
                if tally.lane is lane and tally.status is status
            )

        lanes: list[LaneView] = []
        for lane in JobLane:
            due: int = int(self._health.count_due_jobs(lane, now))
            oldest = self._health.find_oldest_due_job(lane, now) if due else None
            lanes.append(
                LaneView(
                    lane=lane,
                    waiting=LaneJobCount(due),
                    scheduled=LaneJobCount(
                        max(0, count(lane, QueuedJobStatus.PENDING) - due)
                    ),
                    running=LaneJobCount(count(lane, QueuedJobStatus.RUNNING)),
                    dead=LaneJobCount(count(lane, QueuedJobStatus.DEAD)),
                    oldest_wait_seconds=(
                        None
                        if oldest is None
                        else WaitSeconds(
                            max(0, int(now) - int(oldest.run_at))
                            // MICROSECONDS_PER_SECOND
                        )
                    ),
                )
            )

        return lanes

    def _measure_database(self) -> DatabaseSize | None:
        try:
            return self._database_size.measure()
        except ApplicationError as error:
            logger.warning("The database size could not be read: %s", error)
            return None
