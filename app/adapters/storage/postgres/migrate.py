"""
Apply the SQL migrations in `migrations/` to the database in DATABASE_URL.

    uv run python -m app.adapters.storage.postgres.migrate            # apply
    uv run python -m app.adapters.storage.postgres.migrate --dry-run  # list

Safe to run on every deploy and from several instances at once. Exit codes:
0 done, 1 a migration could not be applied, 2 DATABASE_URL is not set.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.postgres.postgres_schema_migration_store_adapter import (
    PostgresSchemaMigrationStoreAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.storage import (
    ApplyDatabaseMigrationsCommand,
    DatabaseMigrationsReport,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

DEFAULT_MIGRATIONS_DIRECTORY: Path = Path(__file__).resolve().parents[4] / "migrations"
EXIT_OK: int = 0
EXIT_MIGRATION_FAILED: int = 1
EXIT_NOT_CONFIGURED: int = 2


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Run the migrations; returns the process exit code."""

    output_stream: TextIO = sys.stdout if output is None else output
    error_stream: TextIO = sys.stderr if error_output is None else error_output
    parsed_arguments: argparse.Namespace = build_argument_parser().parse_args(arguments)
    is_dry_run: bool = bool(parsed_arguments.dry_run)
    migrations_directory: Path = Path(str(parsed_arguments.directory))

    try:
        settings: AppSettings = assemble_app_settings(
            os.environ if environment_variables is None else environment_variables
        )
    except (ApplicationError, ValueError) as error:
        # Typed primitives and enums raise ValueError subclasses.
        print(f"Invalid settings: {error}", file=error_stream)
        return EXIT_NOT_CONFIGURED

    if settings.database_url is None:
        print(
            "DATABASE_URL is not set; nothing to migrate (in-memory storage).",
            file=error_stream,
        )
        return EXIT_NOT_CONFIGURED

    connection_pool = PostgresConnectionPoolClient(
        database_url=settings.database_url,
        max_size=1,
        application_name="assistant-workshop-migrate",
    )
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                ApplyDatabaseMigrationsUseCase(
                    migration_source=SqlFileMigrationSourceAdapter(
                        migrations_directory
                    ),
                    migration_store=PostgresSchemaMigrationStoreAdapter(
                        connection_pool
                    ),
                    wall_clock=WallClock(preferred_time_unit_type=Microseconds),
                )
            )
        )
    )
    try:
        report: DatabaseMigrationsReport = operator.operate(
            ApplyDatabaseMigrationsCommand(is_dry_run=is_dry_run)
        )
    except ApplicationError as error:
        print(f"Migration failed: {error}", file=error_stream)
        return EXIT_MIGRATION_FAILED
    finally:
        connection_pool.close()

    print(describe_report(report, is_dry_run), file=output_stream)
    return EXIT_OK


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.adapters.storage.postgres.migrate",
        description="Apply SQL migrations to the database in DATABASE_URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only list pending migrations",
    )
    parser.add_argument(
        "--directory",
        default=str(DEFAULT_MIGRATIONS_DIRECTORY),
        help="directory with NNNN_slug.sql files (default: %(default)s)",
    )
    return parser


def describe_report(report: DatabaseMigrationsReport, is_dry_run: bool) -> str:
    """Human-readable summary of a run, one line per migration."""

    lines: list[str] = []
    lines.extend(f"applied  {name}" for name in report.newly_applied)
    lines.extend(f"pending  {name}" for name in report.pending)
    lines.extend(
        f"unknown  {name} (recorded in the database, missing from the directory)"
        for name in report.unknown_applied
    )
    if is_dry_run:
        lines.append(
            f"{len(report.pending)} pending, "
            f"{len(report.already_applied)} already applied."
        )
    else:
        lines.append(
            f"Schema is up to date: {len(report.newly_applied)} applied now, "
            f"{len(report.already_applied)} already applied."
        )

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
