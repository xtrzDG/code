"""
The perf suite (`uv run pytest -m perf tests/perf`; excluded by default):
a throwaway Postgres, migrated, filled by `workshop seed-load`'s operator
at PERF_SCALE, and the real application over it (edges faked as in the
end-to-end journeys). Skipped without Postgres binaries.
"""

import time
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.storage.postgres.postgres_schema_migration_store_adapter import (
    PostgresSchemaMigrationStoreAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.load_data import LoadSeedManifest
from app.schemas.dto.storage import ApplyDatabaseMigrationsCommand
from app.schemas.typings.platform.strings import DatabaseUrl
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from tests.e2e.harness import start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.perf.latency import PerfReport
from tests.perf.perf_scale import PerfScale, read_report_path, read_scale
from tests.storage.conftest import (
    migrated_template_database,
    postgres_server,
)
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    is_postgres_available,
    postgres_bin_directory,
)
from tests.storage.storage_testing import (
    MIGRATIONS_DIRECTORY,
    RecordedRetryPause,
    build_fixed_wall_clock,
)

# The reply budget runs on the game days' world (tests/chaos), on the
# throwaway Postgres of the storage tests.
__all__ = ["migrated_template_database", "postgres_server"]


@dataclass(frozen=True)
class PerfTarget:
    """The running application over the seeded database, and its manifest."""

    client: TestClient
    manifest: LoadSeedManifest
    scale: PerfScale


def migrate(database_url: DatabaseUrl) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        ApplyDatabaseMigrationsUseCase(
            migration_source=SqlFileMigrationSourceAdapter(MIGRATIONS_DIRECTORY),
            migration_store=PostgresSchemaMigrationStoreAdapter(pool),
            wall_clock=build_fixed_wall_clock(),
            retry_pause=RecordedRetryPause(),
        ).run(ApplyDatabaseMigrationsCommand())
    finally:
        pool.close()


@pytest.fixture(scope="session")
def perf_report() -> Generator[PerfReport]:
    report = PerfReport(scale=read_scale())
    yield report
    path: str | None = read_report_path()
    if path is not None:
        report.write(Path(path))


@pytest.fixture(scope="session")
def perf_target(perf_report: PerfReport) -> Generator[PerfTarget]:
    bin_directory = postgres_bin_directory()
    if not is_postgres_available(bin_directory):
        pytest.skip(f"Postgres binaries not found in {bin_directory}.")

    server = ThrowawayPostgresServer(bin_directory)
    server.start()
    try:
        database_url: DatabaseUrl = server.app_database_url(server.create_database())
        migrate(database_url)
        workshop = start_workshop({**E2E_ENVIRONMENT, "DATABASE_URL": database_url})
        started: float = time.perf_counter()
        manifest: LoadSeedManifest = (
            workshop.container.operators.demo.seed_load_operator().operate(
                perf_report.scale.command()
            )
        )
        perf_report.seed_seconds = time.perf_counter() - started
        analyze(database_url)
        with TestClient(workshop.application) as client:
            yield PerfTarget(client=client, manifest=manifest, scale=perf_report.scale)
    finally:
        server.stop()


def analyze(database_url: DatabaseUrl) -> None:
    """Fresh planner statistics, as autovacuum keeps them after a bulk load."""

    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        with pool.transaction() as connection:
            connection.execute("analyze")
    finally:
        pool.close()
