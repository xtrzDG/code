"""
Back up the database off-site: a consistent pg_dump, encrypted with age to
BACKUP_AGE_PUBLIC_KEY, uploaded to the EU bucket of BACKUP_S3_*; then the
retention keeps 30 daily and 12 monthly copies (BACKUP_KEEP_*).

    workshop backup                               # Render cron, daily
    uv run python -m app.gateways.cli.backup --work-directory /var/tmp

docs/operations/backup-restore.md has the schedule, the keys and the
restore runbook. Exit codes: 0 done, 1 the backup failed, 2 the backup is
not configured (DATABASE_URL, BACKUP_S3_*, BACKUP_AGE_PUBLIC_KEY).
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO

from typed_time_provider import Microseconds, WallClock

from app.adapters.backup.age_backup_cipher_adapter import AgeBackupCipherAdapter
from app.adapters.backup.pg_dump_database_dump_adapter import (
    PgDumpDatabaseDumpAdapter,
)
from app.gateways.cli.backup_wiring import (
    EXIT_FAILED,
    EXIT_NOT_CONFIGURED,
    EXIT_OK,
    MonitoredRun,
    build_bucket,
    load_settings,
    work_directory,
)
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.backups import CreateDatabaseBackupCommand, DatabaseBackupReport
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.maintenance.backups.create_database_backup_use_case import (
    CreateDatabaseBackupUseCase,
)

# The Sentry Crons monitor `database-backup`: a day without a backup alerts.
BACKUP_JOB: JobName = JobName("database_backup")
BACKUP_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Take one backup; returns the process exit code."""

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
    if settings.database_url is None or backup.bucket is None:
        print(
            "Backups are not configured: set DATABASE_URL, BACKUP_S3_* and "
            "BACKUP_AGE_PUBLIC_KEY (docs/operations/backup-restore.md).",
            file=error_stream,
        )
        return EXIT_NOT_CONFIGURED

    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                CreateDatabaseBackupUseCase(
                    database_dump=PgDumpDatabaseDumpAdapter(
                        settings.database_url, backup.postgres_client_directory
                    ),
                    backup_cipher=AgeBackupCipherAdapter(backup.recipients),
                    backup_bucket=build_bucket(backup.bucket),
                    wall_clock=WallClock(preferred_time_unit_type=Microseconds),
                    prefix=backup.prefix,
                    daily_copies=backup.daily_copies,
                    monthly_copies=backup.monthly_copies,
                )
            )
        )
    )

    def take_backup() -> DatabaseBackupReport:
        with work_directory(parsed.work_directory) as directory:
            return operator.operate(
                CreateDatabaseBackupCommand(work_directory=directory)
            )

    try:
        report: DatabaseBackupReport = MonitoredRun(
            settings, BACKUP_JOB, BACKUP_INTERVAL
        ).run(take_backup, lambda _report: True)
    except Exception as error:  # noqa: BLE001 - reported, then the exit code
        print(f"Backup failed: {error}", file=error_stream)
        return EXIT_FAILED

    print(describe_backup(report), file=output_stream)
    return EXIT_OK


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workshop backup",
        description=(
            "Dump DATABASE_URL, encrypt it with age and upload it to the "
            "backup bucket; then apply the retention."
        ),
    )
    parser.add_argument(
        "--work-directory",
        default=None,
        help="where the temporary dump and archive go (default: the system's "
        "temporary directory); needs room for about twice the dump",
    )
    return parser


def describe_backup(report: DatabaseBackupReport) -> str:
    manifest = report.manifest
    facts = manifest.facts
    lines: list[str] = [
        f"Uploaded {manifest.archive_key} ({int(manifest.archive_size)} bytes, "
        f"SHA-256 {manifest.archive_checksum}).",
        f"Snapshot: {len(facts.row_counts)} tables, "
        f"{sum(int(count) for count in facts.row_counts.values())} rows, "
        f"{len(facts.applied_migrations)} migrations, "
        f"{len(facts.secured_tables)} tables under row-level security.",
        f"Retention: {len(report.kept_keys)} backups kept, "
        f"{len(report.deleted_keys)} deleted.",
    ]
    lines.extend(f"deleted  {key}" for key in report.deleted_keys)
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
