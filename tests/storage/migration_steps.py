"""Steps of the migration tests: run migrations, copy them, list the tables."""

import shutil
from pathlib import Path

from app.adapters.storage.postgres.postgres_schema_migration_store_adapter import (
    PostgresSchemaMigrationStoreAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.storage import (
    ApplyDatabaseMigrationsCommand,
    DatabaseMigrationsReport,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY, build_fixed_wall_clock

MIGRATION_NAMES: list[str] = sorted(
    path.stem for path in MIGRATIONS_DIRECTORY.glob("*.sql")
)


def run_migrations(
    database_url: DatabaseUrl,
    migrations_directory: Path = MIGRATIONS_DIRECTORY,
    is_dry_run: bool = False,
) -> DatabaseMigrationsReport:
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        return ApplyDatabaseMigrationsUseCase(
            migration_source=SqlFileMigrationSourceAdapter(migrations_directory),
            migration_store=PostgresSchemaMigrationStoreAdapter(connection_pool),
            wall_clock=build_fixed_wall_clock(),
        ).run(ApplyDatabaseMigrationsCommand(is_dry_run=is_dry_run))
    finally:
        connection_pool.close()


def copy_migrations(target_directory: Path) -> Path:
    target_directory.mkdir()
    for source_path in MIGRATIONS_DIRECTORY.glob("*.sql"):
        shutil.copy(source_path, target_directory / source_path.name)

    return target_directory


def workshop_tables(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> set[str]:
    with postgres_server.admin_connection(database_name) as connection:
        rows = connection.execute(
            "select tablename from pg_tables where schemaname = 'workshop'"
        ).fetchall()

    return {str(row[0]) for row in rows}
