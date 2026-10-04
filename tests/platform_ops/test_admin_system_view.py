"""
GET /v1/admin/system's use case in memory: lanes and dead letters, worker
pulses, channels that need the team, the database size, backups and the
platform alerts, for platform admins only.
"""

import pytest

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.monitoring import (
    AlertUnit,
    MaintenanceRunKind,
    MaintenanceRunOutcome,
    PlatformAlertCode,
    PlatformAlertStatus,
)
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_system import AdminSystemQuery, TableSizeView
from app.schemas.dto.platform_health import DatabaseSize
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
)
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.schemas.typings.backups.constrained_strings import DatabaseTableName
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
    CollectionRowEstimate,
    NotificationCount,
    StorageByteSize,
)
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.system.get_admin_system_use_case import (
    GetAdminSystemUseCase,
)
from tests.platform_ops.ops_documents import (
    DAY,
    HOUR,
    MINUTE,
    NOW,
    at,
    business,
    channel,
    job,
    pulse,
)
from tests.platform_ops.ops_world import OpsWorld, put

ADMIN: UserId = UserId()


class AdminsOnly(UseCaseContract[UserId, UserDocument]):
    def run(self, input_data: UserId) -> UserDocument:
        if input_data != ADMIN:
            raise AccessDeniedError("Platform admins only.")
        return UserDocument.model_construct(id=ADMIN)


class MeasuredDatabase:
    def __init__(self, size: DatabaseSize | None, fails: bool = False) -> None:
        self._size: DatabaseSize | None = size
        self._fails: bool = fails

    def measure(self) -> DatabaseSize | None:
        if self._fails:
            raise ExternalServiceError("pg_class is not readable.")
        return self._size


DATABASE = DatabaseSize(
    total_bytes=StorageByteSize(9_000_000),
    tables=[
        TableSizeView(
            table=DatabaseTableName("workshop.messages"),
            total_bytes=StorageByteSize(6_000_000),
            row_estimate=CollectionRowEstimate(42_000),
        )
    ],
)


def system_page(
    world: OpsWorld, database: MeasuredDatabase | None = None
) -> GetAdminSystemUseCase:
    return GetAdminSystemUseCase(
        authorize_platform_admin=AdminsOnly(),
        system_health_repo=world.health_repo,
        maintenance_run_repo=world.run_repo,
        alert_state_repo=world.alert_state_repo,
        database_size=database or MeasuredDatabase(DATABASE),
        backup_max_age=BackupFreshnessHours(26),
        wall_clock=world.clock.wall_clock,
    )


def backup(finished_at: int, outcome: MaintenanceRunOutcome) -> MaintenanceRunDocument:
    return MaintenanceRunDocument(
        kind=MaintenanceRunKind.BACKUP,
        outcome=outcome,
        started_at=at(finished_at - 5 * MINUTE),
        finished_at=at(finished_at),
        created_at=at(finished_at),
        updated_at=at(finished_at),
    )


def alert(
    code: PlatformAlertCode, resolved_hours_ago: int | None
) -> PlatformAlertStateDocument:
    resolved = None if resolved_hours_ago is None else at(-resolved_hours_ago * HOUR)
    return PlatformAlertStateDocument(
        code=code,
        status=(
            PlatformAlertStatus.FIRING
            if resolved is None
            else PlatformAlertStatus.RESOLVED
        ),
        figure=AlertFigure(3),
        threshold=AlertThreshold(0),
        unit=AlertUnit.COUNT,
        detail=AlertDetailText("Three of them."),
        fired_at=at(-2 * DAY),
        checked_at=NOW,
        notification_count=NotificationCount(1),
        resolved_at=resolved,
        created_at=at(-2 * DAY),
        updated_at=NOW,
    )


def test_lanes_count_waiting_scheduled_running_and_dead_jobs() -> None:
    world = OpsWorld()
    put(
        world.jobs,
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-3 * MINUTE)),
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-MINUTE)),
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(HOUR)),
        job(QueuedJobStatus.RUNNING, JobLane.OUTBOUND),
        job(QueuedJobStatus.DEAD, JobLane.DEFAULT, name="import_website"),
        job(QueuedJobStatus.DEAD, JobLane.OUTBOUND, name="deliver_outbound"),
        job(QueuedJobStatus.DEAD, JobLane.OUTBOUND, name="deliver_outbound"),
        job(QueuedJobStatus.DONE, JobLane.INBOUND),
    )

    view = system_page(world).run(AdminSystemQuery(user_id=ADMIN))

    lanes = {lane.lane: lane for lane in view.lanes}
    inbound, outbound = lanes[JobLane.INBOUND], lanes[JobLane.OUTBOUND]
    assert (int(inbound.waiting), int(inbound.scheduled)) == (2, 1)
    assert int(inbound.oldest_wait_seconds or 0) == 180
    assert (int(outbound.running), int(outbound.dead)) == (1, 2)
    assert lanes[JobLane.AUTOTESTS].oldest_wait_seconds is None
    assert [(str(dead.name), int(dead.count)) for dead in view.dead_jobs] == [
        ("deliver_outbound", 2),
        ("import_website", 1),
    ]


def test_channels_workers_and_the_database_are_shown() -> None:
    world = OpsWorld()
    salon = business("Salon Ia")
    put(world.businesses, salon)
    put(
        world.channels,
        channel(salon.id, ChannelStatus.ERROR),
        channel(salon.id, expires_at=at(3 * DAY)),
        channel(salon.id, expires_at=at(-DAY)),
        channel(salon.id, expires_at=at(60 * DAY)),
    )
    put(world.pulses, pulse("worker-a", at(-MINUTE)), pulse("worker-b", at(-HOUR)))

    view = system_page(world).run(AdminSystemQuery(user_id=ADMIN))

    [broken] = view.channels_in_error
    assert str(broken.business_name) == "Salon Ia" and broken.last_error
    assert int(view.channels_in_error_count) == 1
    expiring = sorted(view.expiring_credentials, key=lambda issue: issue.is_expired)
    assert [issue.is_expired for issue in expiring] == [False, True]
    assert [(worker.host_name, worker.is_stale) for worker in view.workers] == [
        ("worker-a", False),
        ("worker-b", True),
    ]
    assert int(view.database_bytes or 0) == 9_000_000
    assert [str(table.table) for table in view.tables] == ["workshop.messages"]


def test_an_old_or_failed_backup_is_overdue() -> None:
    fresh, failed, old, none = OpsWorld(), OpsWorld(), OpsWorld(), OpsWorld()
    put(fresh.runs, backup(-2 * HOUR, MaintenanceRunOutcome.SUCCEEDED))
    put(failed.runs, backup(-30 * DAY, MaintenanceRunOutcome.SUCCEEDED))
    put(failed.runs, backup(-HOUR, MaintenanceRunOutcome.FAILED))
    put(old.runs, backup(-27 * HOUR, MaintenanceRunOutcome.SUCCEEDED))

    views = {
        name: system_page(world).run(AdminSystemQuery(user_id=ADMIN))
        for name, world in (("fresh", fresh), ("failed", failed), ("old", old))
    }
    unknown = system_page(none).run(AdminSystemQuery(user_id=ADMIN))

    assert not views["fresh"].is_backup_overdue
    assert views["failed"].is_backup_overdue
    assert views["failed"].last_backup is not None
    assert views["failed"].last_backup.outcome is MaintenanceRunOutcome.FAILED
    assert views["old"].is_backup_overdue
    assert unknown.is_backup_overdue and unknown.last_backup is None


def test_firing_alerts_come_first_and_old_episodes_are_left_out() -> None:
    world = OpsWorld()
    for state in (
        alert(PlatformAlertCode.TOOL_ERRORS, None),
        alert(PlatformAlertCode.LLM_ERRORS, None),
        alert(PlatformAlertCode.DEAD_JOBS, 2),
        alert(PlatformAlertCode.OTP_CAP_TRIPS, 30),
    ):
        world.alert_state_repo.save(state)

    view = system_page(world).run(AdminSystemQuery(user_id=ADMIN))

    assert [(state.code, state.status) for state in view.alerts] == [
        (PlatformAlertCode.LLM_ERRORS, PlatformAlertStatus.FIRING),
        (PlatformAlertCode.TOOL_ERRORS, PlatformAlertStatus.FIRING),
        (PlatformAlertCode.DEAD_JOBS, PlatformAlertStatus.RESOLVED),
    ]
    assert str(view.alerts[0].runbook).endswith("llm-outage.md")


def test_an_unreadable_database_size_leaves_the_rest() -> None:
    world = OpsWorld()

    view = system_page(world, MeasuredDatabase(None, fails=True)).run(
        AdminSystemQuery(user_id=ADMIN)
    )

    assert view.database_bytes is None and view.tables == []
    assert len(view.lanes) == len(JobLane)


def test_only_platform_admins_see_the_page() -> None:
    with pytest.raises(AccessDeniedError):
        system_page(OpsWorld()).run(AdminSystemQuery(user_id=UserId()))
