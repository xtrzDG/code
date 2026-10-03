"""
The restore drill: restore the newest off-site backup into a throwaway
database and prove it is complete and safe.

    workshop restore-check                         # weekly, and nightly in CI
    workshop restore-check --archive workshop/2026/10/20261003T010700Z.pgdump.age
    workshop restore-check --keep-database         # keep it: a real restore

It needs the bucket (BACKUP_S3_*), the private key (BACKUP_AGE_IDENTITY)
and a throwaway Postgres server with a role that may create databases
(RESTORE_CHECK_DATABASE_URL), never production's. The checks: the archive
matches its manifest; every table has the dumped number of rows; the
migrations are this checkout's; row-level security isolates businesses;
the newest backup is at most BACKUP_MAX_AGE_HOURS old. Exit codes: 0 the
backup restores, 1 a check failed or the restore failed, 2 not configured.
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
from app.gateways.cli.migrate import DEFAULT_MIGRATIONS_DIRECTORY
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.backups import CheckBackupRestoreCommand, RestoreCheckReport
from app.schemas.exceptions.backup_errors import RestoreDrillFailedError
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.maintenance.backups.check_backup_restore_use_case import (
    CheckBackupRestoreUseCase,
)
from app.utilities.backups.backup_keys import to_datetime

# The Sentry Crons monitor `restore-drill`: a week without a proven
# restore alerts.
RESTORE_DRILL_JOB: JobName = JobName("restore_drill")
RESTORE_DRILL_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(7 * 24 * 60 * 60)


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
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

    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                CheckBackupRestoreUseCase(
                    backup_bucket=build_bucket(backup.bucket),
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
    try:
        report: RestoreCheckReport = monitored.run(
            run_drill, lambda result: not result.problems
        )
    except Exception as error:  # noqa: BLE001 - reported, then the exit code
        print(f"Restore drill failed: {error}", file=error_stream)
        return EXIT_FAILED

    print(describe_drill(report, bool(parsed.keep_database)), file=output_stream)
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
        "--migrations",
        default=str(DEFAULT_MIGRATIONS_DIRECTORY),
        help="the checkout's migrations to compare with (default: %(default)s)",
    )
    return parser


def describe_drill(report: RestoreCheckReport, is_kept: bool) -> str:
    facts = report.restored.facts
    taken: str = to_datetime(report.archive_created_at).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"Restored {report.archive_key} (taken {taken}) into "
        f"{report.restored.scratch_database}"
        + (" (kept)." if is_kept else " (dropped again)."),
        f"{len(facts.row_counts)} tables, "
        f"{sum(int(count) for count in facts.row_counts.values())} rows, "
        f"{len(facts.applied_migrations)} migrations; row-level security "
        f"probed on {len(report.restored.isolation_probes)} tables.",
    ]
    if report.pending_migrations:
        lines.append(
            f"{len(report.pending_migrations)} migrations of this checkout are "
            "newer than the backup: "
            + ", ".join(str(name) for name in report.pending_migrations)
        )
    lines.extend(f"FAILED  {problem}" for problem in report.problems)
    lines.append(
        f"{len(report.problems)} checks failed."
        if report.problems
        else "OK: the backup restores completely and isolates businesses."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
