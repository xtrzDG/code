"""
Fill trigger-kept lookup columns for rows written before their migration.

    workshop backfill-lookup                                  # every column
    workshop backfill-lookup --collection contacts --field last_seen_at
    workshop backfill-lookup --collection contacts --batch 5000
    workshop backfill-lookup --dry-run                        # only count

(`uv run python -m app.gateways.cli.backfill_lookup ...` without the image.)
Run it after a deploy whose migration added a lookup column in the
online-safe pattern (migrations/README.md), never in `preDeployCommand`:
it walks each table in primary-key order, one short transaction per batch,
platform-wide, and fills only empty columns, so it is idempotent and safe
while the application writes. Exit codes: 0 done, 1 the backfill failed,
2 DATABASE_URL is not set, the settings are invalid or no such column.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO

from app.adapters.storage.postgres.postgres_lookup_backfill_adapter import (
    PostgresLookupBackfillAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.lookup_backfill import (
    DEFAULT_LOOKUP_BACKFILL_BATCH_SIZE,
    BackfillLookupColumnsCommand,
    LookupBackfillReport,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.storage.constrained_integers import (
    LockWaitSeconds,
    LookupBackfillBatchSize,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.use_cases.maintenance.backfill_lookup_columns_use_case import (
    BackfillLookupColumnsUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.migration_retry_pause import JitteredMigrationRetryPause

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_NOT_CONFIGURED: int = 2
# One batch per statement: longer than a request, bounded all the same.
BATCH_STATEMENT_TIMEOUT_SECONDS: int = 5 * 60


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Run the backfill; returns the process exit code."""

    output_stream: TextIO = sys.stdout if output is None else output
    error_stream: TextIO = sys.stderr if error_output is None else error_output
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    try:
        command = BackfillLookupColumnsCommand(
            collection_name=(
                None
                if parsed.collection is None
                else DocumentCollectionName(str(parsed.collection))
            ),
            field=None
            if parsed.field is None
            else DocumentFieldPath(str(parsed.field)),
            batch_size=LookupBackfillBatchSize(int(parsed.batch)),
            is_dry_run=bool(parsed.dry_run),
        )
        lock_timeout = LockWaitSeconds(int(parsed.lock_timeout))
        settings: AppSettings = assemble_app_settings(
            os.environ if environment_variables is None else environment_variables
        )
    except (ApplicationError, ValueError) as error:
        print(f"Invalid arguments or settings: {error}", file=error_stream)
        return EXIT_NOT_CONFIGURED

    if settings.database_url is None:
        print(
            "DATABASE_URL is not set; in-memory storage has no lookup columns.",
            file=error_stream,
        )
        return EXIT_NOT_CONFIGURED

    connection_pool = PostgresConnectionPoolClient(
        database_url=settings.database_url,
        max_size=1,
        application_name="assistant-workshop-backfill-lookup",
        statement_timeout_seconds=BATCH_STATEMENT_TIMEOUT_SECONDS,
        idle_in_transaction_timeout_seconds=BATCH_STATEMENT_TIMEOUT_SECONDS,
    )
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                BackfillLookupColumnsUseCase(
                    backfill=PostgresLookupBackfillAdapter(
                        connection_pool, lock_timeout=lock_timeout
                    ),
                    retry_pause=JitteredMigrationRetryPause(),
                )
            )
        )
    )
    try:
        report: LookupBackfillReport = operator.operate(command)
    except NotFoundError as error:
        print(str(error), file=error_stream)
        return EXIT_NOT_CONFIGURED
    except ApplicationError as error:
        print(f"Backfill failed: {error}", file=error_stream)
        return EXIT_FAILED
    finally:
        connection_pool.close()

    print(describe_report(report), file=output_stream)
    return EXIT_OK


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workshop backfill-lookup",
        description=(
            "Fill trigger-kept lookup columns of rows written before their "
            "migration (DATABASE_URL, all businesses)."
        ),
    )
    parser.add_argument("--collection", metavar="NAME", help="only this table")
    parser.add_argument(
        "--field", metavar="FIELD", help="only this field (needs --collection)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=int(DEFAULT_LOOKUP_BACKFILL_BATCH_SIZE),
        help="rows per transaction, 1 to 50000 (default: %(default)s)",
    )
    parser.add_argument(
        "--lock-timeout",
        type=int,
        default=5,
        help="seconds a batch may wait for a locked row (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="only count the rows to fill"
    )
    return parser


def describe_report(report: LookupBackfillReport) -> str:
    """One line per column, then a total."""

    if report.is_dry_run:
        lines: list[str] = [
            f"missing  {entry.collection_name}.{entry.field}: {int(entry.missing)} rows"
            for entry in report.columns
        ]
        total: int = sum(int(entry.missing) for entry in report.columns)
        lines.append(f"{len(report.columns)} columns checked: {total} rows to fill.")
        return "\n".join(lines)

    lines = [
        f"filled   {entry.collection_name}.{entry.field}: {int(entry.filled)} of "
        f"{int(entry.scanned)} rows in {int(entry.batch_count)} batches"
        for entry in report.columns
    ]
    filled: int = sum(int(entry.filled) for entry in report.columns)
    lines.append(f"{len(report.columns)} columns backfilled: {filled} rows filled.")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
