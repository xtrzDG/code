"""
The restore drill: restore the newest off-site backup into a throwaway
database and prove it is complete and safe.

    workshop restore-check                         # weekly, and nightly in CI
    workshop restore-check --archive workshop/2026/10/20261003T010700Z.pgdump.age
    workshop restore-check --keep-database         # keep it: a real restore
    workshop restore-check --report "$GITHUB_STEP_SUMMARY"   # timings, checks

It needs the bucket (BACKUP_S3_*), the private key (BACKUP_AGE_IDENTITY)
and a throwaway Postgres server with a role that may create databases
(RESTORE_CHECK_DATABASE_URL), never production's. The checks: the archive
matches its manifest; every table has the dumped number of rows; the
migrations are this checkout's; row-level security isolates businesses;
the newest backup is at most BACKUP_MAX_AGE_HOURS old; after the deletion
ledger (its copy in the bucket and the restored database's own) is applied,
no row of a deleted business is left; the erased customers the backup holds
with their data again are counted. With DATABASE_URL
(the weekly Render cron) the drill is recorded for the admin system page.
Exit codes: 0 the backup restores, 1 a check failed or the restore failed,
2 not configured.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from typed_time_provider import Microseconds, WallClock

from app.adapters.backup.age_backup_cipher_adapter import AgeBackupCipherAdapter
from app.adapters.backup.pg_restore_scratch_database_adapter import (
    PgRestoreScratchDatabaseAdapter,
)
from app.adapters.business_closures.bucket_contact_erasure_ledger_adapter import (
    BucketContactErasureLedgerAdapter,
)
from app.adapters.business_closures.bucket_deletion_ledger_mirror_adapter import (
    BucketDeletionLedgerMirrorAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.gateways.cli.backup_wiring import (
    EXIT_FAILED,
    EXIT_NOT_CONFIGURED,
    EXIT_OK,
    build_bucket,
    load_settings,
    monitored_run,
    work_directory,
)
from app.gateways.cli.maintenance_run_log import (
    RecordRun,
    describe_failure,
    record_maintenance_run,
    record_with_container,
)
from app.gateways.cli.migrate import DEFAULT_MIGRATIONS_DIRECTORY
from app.gateways.cli.restore_drill_report import (
    append_report,
    describe_drill,
    describe_timings,
    failure_report,
    markdown_report,
)
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.monitoring import MaintenanceRunKind, MaintenanceRunOutcome
from app.schemas.dto.backups import CheckBackupRestoreCommand, RestoreCheckReport
from app.schemas.dto.maintenance_runs import RecordMaintenanceRunCommand
from app.schemas.exceptions.backup_errors import RestoreDrillFailedError
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.schemas.typings.monitoring.constrained_integers import ArchivedRowCount
from app.schemas.typings.monitoring.strings import MaintenanceErrorText
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.maintenance.backups.check_backup_restore_use_case import (
    CheckBackupRestoreUseCase,
)

# The Sentry Crons monitor `restore-drill`: a week without a proven
# restore alerts.
RESTORE_DRILL_JOB: JobName = JobName("restore_drill")
RESTORE_DRILL_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(7 * 24 * 60 * 60)


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
    record_run: RecordRun = record_with_container,
) -> int:
    """Run the drill once; returns the process exit code."""

    output_stream: TextIO = sys.stdout if output is None else output
    error_stream: TextIO = sys.stderr if error_output is None else error_output
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    settings: AppSettings | None = load_settings(
        os.environ if environment_variables is None else environment_variables,
        error_stream,
    )
    if settings is None:
        return EXIT_NOT_CONFIGURED

    backup = settings.backup
    if (
        backup.bucket is None
        or backup.identity is None
        or backup.restore_check_database_url is None
    ):
        print(
            "The restore drill is not configured: set BACKUP_S3_*, "
            "BACKUP_AGE_IDENTITY and RESTORE_CHECK_DATABASE_URL "
            "(docs/operations/backup-restore.md).",
            file=error_stream,
        )
        return EXIT_NOT_CONFIGURED

    bucket = build_bucket(backup.bucket)
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                CheckBackupRestoreUseCase(
                    backup_bucket=bucket,
                    backup_cipher=AgeBackupCipherAdapter(
                        backup.recipients, backup.identity
                    ),
                    scratch_database=PgRestoreScratchDatabaseAdapter(
                        backup.restore_check_database_url,
                        backup.postgres_client_directory,
                    ),
                    migration_source=SqlFileMigrationSourceAdapter(
                        Path(str(parsed.migrations))
                    ),
                    wall_clock=WallClock(preferred_time_unit_type=Microseconds),
                    prefix=backup.prefix,
                    max_age=backup.max_age_hours,
                    ledger_mirror=BucketDeletionLedgerMirrorAdapter(
                        bucket, backup.prefix
                    ),
                    contact_erasure_ledger=BucketContactErasureLedgerAdapter(
                        bucket, backup.prefix
                    ),
                )
            )
        )
    )

    def run_drill() -> RestoreCheckReport:
        with work_directory(parsed.work_directory) as directory:
            return operator.operate(
                CheckBackupRestoreCommand(
                    work_directory=directory,
                    archive_key=(
                        None
                        if parsed.archive is None
                        else BackupObjectKey(str(parsed.archive))
                    ),
                    is_scratch_database_kept=bool(parsed.keep_database),
                )
            )

    monitored = monitored_run(settings, RESTORE_DRILL_JOB, RESTORE_DRILL_INTERVAL)
    clock = WallClock(preferred_time_unit_type=Microseconds)
    started_at: Microseconds = clock.now_unix()
    try:
        report: RestoreCheckReport = monitored.run(
            run_drill, lambda result: not result.problems
        )
    except Exception as error:  # noqa: BLE001 - reported, then the exit code
        print(f"Restore drill failed: {error}", file=error_stream)
        if parsed.report is not None:
            append_report(Path(parsed.report), failure_report(str(error), started_at))
        failed = RecordMaintenanceRunCommand(
            kind=MaintenanceRunKind.RESTORE_DRILL,
            outcome=MaintenanceRunOutcome.FAILED,
            started_at=started_at,
            finished_at=clock.now_unix(),
            error=describe_failure(error),
        )
        record_maintenance_run(settings, failed, error_stream, record_run)
        return EXIT_FAILED

    finished_at: Microseconds = clock.now_unix()
    is_kept: bool = bool(parsed.keep_database)
    print(describe_drill(report, is_kept), file=output_stream)
    print(describe_timings(report, started_at, finished_at), file=output_stream)
    if parsed.report is not None:
        append_report(
            Path(parsed.report),
            markdown_report(report, is_kept, started_at, finished_at),
        )
    record_maintenance_run(
        settings, drill_run(report, started_at, clock), error_stream, record_run
    )
    if report.problems:
        monitored.report_failure(
            RestoreDrillFailedError(
                f"The restore drill of {report.archive_key} failed "
                f"{len(report.problems)} checks: "
                + " ".join(str(problem) for problem in report.problems)
            )
        )
        return EXIT_FAILED

    return EXIT_OK


def drill_run(
    report: RestoreCheckReport,
    started_at: Microseconds,
    clock: WallClock[Microseconds],
) -> RecordMaintenanceRunCommand:
    """The finished drill as the system page records it (failed checks: FAILED)."""

    facts = report.restored.facts
    return RecordMaintenanceRunCommand(
        kind=MaintenanceRunKind.RESTORE_DRILL,
        outcome=(
            MaintenanceRunOutcome.FAILED
            if report.problems
            else MaintenanceRunOutcome.SUCCEEDED
        ),
        started_at=started_at,
        finished_at=clock.now_unix(),
        archive_key=report.archive_key,
        archive_size=report.manifest.archive_size,
        row_count=ArchivedRowCount(
            sum(int(count) for count in facts.row_counts.values())
        ),
        error=(
            MaintenanceErrorText(
                f"{len(report.problems)} checks failed: {report.problems[0]}"
            )
            if report.problems
            else None
        ),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workshop restore-check",
        description=(
            "Restore the newest backup into a throwaway database of "
            "RESTORE_CHECK_DATABASE_URL and check it."
        ),
    )
    parser.add_argument("--archive", default=None, help="restore this archive key")
    parser.add_argument(
        "--keep-database",
        action="store_true",
        help="keep the restored database (its name is printed)",
    )
    parser.add_argument(
        "--work-directory",
        default=None,
        help="where the downloaded archive and dump go (default: the system's "
        "temporary directory)",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="append the drill's Markdown report (timings and checks) to this "
        "file, e.g. the workflow's $GITHUB_STEP_SUMMARY",
    )
    parser.add_argument(
        "--migrations",
        default=str(DEFAULT_MIGRATIONS_DIRECTORY),
        help="the checkout's migrations to compare with (default: %(default)s)",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
