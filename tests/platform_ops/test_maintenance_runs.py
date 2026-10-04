"""
The backup and restore drill commands record how each run ended for the
admin system page: what is recorded, when (only with DATABASE_URL), and
that recording never changes the command's own outcome.
"""

import io

from app.gateways.cli.backup import backup_run
from app.gateways.cli.maintenance_run_log import (
    describe_failure,
    record_maintenance_run,
)
from app.gateways.cli.restore_check import drill_run
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.monitoring import MaintenanceRunKind, MaintenanceRunOutcome
from app.schemas.dto.backups import (
    BackupManifest,
    DatabaseBackupReport,
    RestoreCheckReport,
    RestoredDatabase,
)
from app.schemas.dto.maintenance_runs import RecordMaintenanceRunCommand
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_integers import BackupArchiveSize
from app.schemas.typings.backups.constrained_strings import (
    BackupChecksum,
    BackupObjectKey,
    ScratchDatabaseName,
)
from app.schemas.typings.backups.strings import RestoreCheckProblem
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.use_cases.admin.system.record_maintenance_run_use_case import (
    RecordMaintenanceRunUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.backups.backup_fakes import build_facts
from tests.platform_ops.ops_documents import MINUTE, at
from tests.platform_ops.ops_world import OpsWorld

ARCHIVE: BackupObjectKey = BackupObjectKey(
    "workshop/2026/10/workshop-20261005T080000Z.pgdump.age"
)
MANIFEST = BackupManifest(
    archive_key=ARCHIVE,
    created_at=at(-5 * MINUTE),
    archive_size=BackupArchiveSize(123_456),
    archive_checksum=BackupChecksum("b" * 64),
    facts=build_facts(bookings=40),
)


def settings(database_url: str | None) -> AppSettings:
    environment = {"APP_ENV": "test"}
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    return assemble_app_settings(environment)


def finished(outcome: MaintenanceRunOutcome) -> RecordMaintenanceRunCommand:
    return RecordMaintenanceRunCommand(
        kind=MaintenanceRunKind.BACKUP,
        outcome=outcome,
        started_at=at(-5 * MINUTE),
        finished_at=at(0),
    )


def test_a_backup_is_recorded_with_its_archive_and_row_total() -> None:
    world = OpsWorld()
    command = backup_run(
        DatabaseBackupReport(manifest=MANIFEST),
        at(-6 * MINUTE),
        world.clock.wall_clock,
    )

    view = RecordMaintenanceRunUseCase(
        world.run_repo, ReleaseVersion("4718714c0f2e"), world.clock.wall_clock
    ).run(command)

    assert command.outcome is MaintenanceRunOutcome.SUCCEEDED
    assert command.archive_key == ARCHIVE
    assert int(command.row_count or 0) == 40 + 2 + 1
    assert view.release == ReleaseVersion("4718714c0f2e")
    latest = world.run_repo.find_latest(MaintenanceRunKind.BACKUP)
    assert latest is not None and int(latest.archive_size or 0) == 123_456
    assert world.run_repo.find_latest(MaintenanceRunKind.RESTORE_DRILL) is None


def test_a_drill_with_failed_checks_is_recorded_as_failed() -> None:
    world = OpsWorld()
    restored = RestoredDatabase(
        scratch_database=ScratchDatabaseName("restore_drill_20261005t080000_3f9a1c"),
        facts=build_facts(bookings=39),
    )
    report = RestoreCheckReport(
        archive_key=ARCHIVE,
        archive_created_at=at(-60 * MINUTE),
        manifest=MANIFEST,
        restored=restored,
        problems=[
            RestoreCheckProblem("workshop.bookings: 39 rows restored, 40 dumped"),
            RestoreCheckProblem("workshop.bookings: row-level security is off"),
        ],
    )

    command = drill_run(report, at(-10 * MINUTE), world.clock.wall_clock)

    assert command.kind is MaintenanceRunKind.RESTORE_DRILL
    assert command.outcome is MaintenanceRunOutcome.FAILED
    assert str(command.error) == (
        "2 checks failed: workshop.bookings: 39 rows restored, 40 dumped"
    )
    clean = drill_run(
        report.model_copy(update={"problems": []}),
        at(-10 * MINUTE),
        world.clock.wall_clock,
    )
    assert clean.outcome is MaintenanceRunOutcome.SUCCEEDED and clean.error is None


def test_only_a_command_with_the_database_records() -> None:
    recorded: list[RecordMaintenanceRunCommand] = []

    def record(_: AppSettings, command: RecordMaintenanceRunCommand) -> None:
        recorded.append(command)

    errors = io.StringIO()
    record_maintenance_run(
        settings(None), finished(MaintenanceRunOutcome.SUCCEEDED), errors, record
    )
    record_maintenance_run(
        settings("postgresql://workshop@localhost/workshop"),
        finished(MaintenanceRunOutcome.FAILED),
        errors,
        record,
    )

    assert [command.outcome for command in recorded] == [MaintenanceRunOutcome.FAILED]
    assert errors.getvalue() == ""


def test_a_run_that_cannot_be_recorded_is_only_reported() -> None:
    def refuse(_: AppSettings, __: RecordMaintenanceRunCommand) -> None:
        raise ExternalServiceError("The database refused the connection.")

    errors = io.StringIO()
    record_maintenance_run(
        settings("postgresql://workshop@localhost/workshop"),
        finished(MaintenanceRunOutcome.SUCCEEDED),
        errors,
        refuse,
    )

    assert "not recorded for the system page" in errors.getvalue()
    assert "refused the connection" in errors.getvalue()


def test_a_failure_is_described_by_its_first_line() -> None:
    long_line = "x" * 900

    assert str(describe_failure(RuntimeError("pg_dump: error\nmore"))) == (
        "pg_dump: error"
    )
    assert len(str(describe_failure(RuntimeError(long_line)))) == 500
    assert str(describe_failure(RuntimeError(""))) == "RuntimeError"
