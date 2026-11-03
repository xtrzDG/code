"""
Rehearse the pending migrations on a production-sized copy (REL-08,
docs/operations/deploys.md, "Migration rehearsal"):

    uv run python -m scripts.migration_rehearsal --base-ref origin/release
    uv run python -m scripts.migration_rehearsal --scale medium --messages 500000 \\
        --report perf/results/migrations.json

1. A throwaway Postgres 16 (POSTGRES_BIN_DIRECTORY, as the storage tests)
   gets the migrations production already ran: every file the commit
   `--base-ref` has (the `release` branch production deploys), or all but
   the newest three when git cannot read that ref.
2. The synthetic dataset fills it (`--scale`: full is 2,000,000 messages
   of 500 businesses, and contacts, conversations, bookings, inbound and
   outbound events in proportion; `--messages` and `--businesses`
   override), and the planner's statistics are refreshed.
3. Each pending migration runs alone through the real runner (lock
   timeout, retries, no-transaction files) and is timed.

The report (JSON with `--report`, Markdown on stdout for the job summary)
lists every pending migration and its seconds. Exit code 1: a migration
failed or took longer than `--budget-seconds` (300); 2: no Postgres
binaries.
"""

import argparse
import shutil
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from app.schemas.typings.platform.strings import DatabaseUrl
from scripts.migration_rehearsal_plan import (
    DEFAULT_BUDGET_SECONDS,
    MIGRATION_SUFFIX,
    SCALES,
    DatasetSize,
    MigrationTiming,
    RehearsalPlan,
    RehearsalReport,
    migration_names,
    names_at_ref,
    plan_rehearsal,
)
from scripts.migration_rehearsal_seed import seed_statements
from tests.storage.migration_steps import run_migrations
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    is_postgres_available,
    postgres_bin_directory,
)
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY

DEFAULT_BASE_REF: str = "origin/release"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uv run python -m scripts.migration_rehearsal",
        description="Time every pending migration against a production-sized copy.",
    )
    parser.add_argument("--base-ref", default=DEFAULT_BASE_REF)
    parser.add_argument("--scale", choices=sorted(SCALES), default="full")
    parser.add_argument("--messages", type=int, help="override the scale's messages")
    parser.add_argument("--businesses", type=int, help="override its businesses")
    parser.add_argument("--budget-seconds", type=float, default=DEFAULT_BUDGET_SECONDS)
    parser.add_argument("--report", type=Path, help="write the JSON report here")
    parser.add_argument("--migrations", type=Path, default=MIGRATIONS_DIRECTORY)
    return parser


def dataset_size(
    scale: str, messages: int | None, businesses: int | None
) -> DatasetSize:
    base: DatasetSize = SCALES[scale]
    return DatasetSize(
        businesses=businesses if businesses is not None else base.businesses,
        messages=messages if messages is not None else base.messages,
    )


def rehearse(
    server: ThrowawayPostgresServer,
    plan: RehearsalPlan,
    size: DatasetSize,
    scale: str,
    budget_seconds: float,
    migrations: Path,
) -> RehearsalReport:
    """Migrate to production's schema, seed, then time each pending file."""

    database: str = server.create_database()
    database_url: DatabaseUrl = server.app_database_url(database)
    with tempfile.TemporaryDirectory(prefix="rehearsal-") as directory:
        staged = Path(directory)
        for name in plan.released:
            shutil.copy(migrations / f"{name}{MIGRATION_SUFFIX}", staged)
        run_migrations(database_url, staged)

        started: float = time.perf_counter()
        seed(server, database, size)
        report = RehearsalReport(
            base=plan.base,
            scale=scale,
            rows=size.per_table,
            seed_seconds=time.perf_counter() - started,
            budget_seconds=budget_seconds,
        )
        for name in plan.pending:
            shutil.copy(migrations / f"{name}{MIGRATION_SUFFIX}", staged)
            report.timings.append(time_migration(database_url, staged, name))
            if report.timings[-1].error is not None:
                break

    return report


def seed(server: ThrowawayPostgresServer, database: str, size: DatasetSize) -> None:
    with server.admin_connection(database) as connection:
        tables: set[str] = {
            str(row[0])
            for row in connection.execute(
                "select tablename from pg_tables where schemaname = 'workshop'"
            ).fetchall()
        }
    with server.app_connection(database) as connection:
        for statement in seed_statements(size.per_table, size.businesses, tables):
            connection.execute(statement.encode("utf-8"))


def time_migration(
    database_url: DatabaseUrl, staged: Path, name: str
) -> MigrationTiming:
    started: float = time.perf_counter()
    try:
        run_migrations(database_url, staged)
    except Exception as error:  # noqa: BLE001 - the report names it
        return MigrationTiming(
            name=name, seconds=time.perf_counter() - started, error=str(error)
        )

    return MigrationTiming(name=name, seconds=time.perf_counter() - started)


def main(arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(arguments)
    bin_directory: Path = postgres_bin_directory()
    if not is_postgres_available(bin_directory):
        print(f"Postgres binaries not found in {bin_directory}.", file=sys.stderr)
        return 2

    plan: RehearsalPlan = plan_rehearsal(
        migration_names(parsed.migrations),
        names_at_ref(parsed.base_ref),
        parsed.base_ref,
    )
    size: DatasetSize = dataset_size(parsed.scale, parsed.messages, parsed.businesses)
    server = ThrowawayPostgresServer(bin_directory)
    server.start()
    try:
        report: RehearsalReport = rehearse(
            server, plan, size, parsed.scale, parsed.budget_seconds, parsed.migrations
        )
    finally:
        server.stop()

    if parsed.report is not None:
        parsed.report.parent.mkdir(parents=True, exist_ok=True)
        parsed.report.write_text(report.to_json(), encoding="utf-8")

    print(report.to_markdown())
    for failure in report.failures:
        print(f"FAILED: {failure}", file=sys.stderr)

    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
