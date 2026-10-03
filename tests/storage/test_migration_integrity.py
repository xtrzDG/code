"""The migration runner against a real Postgres: checksums and safe failures."""

from pathlib import Path

import pytest

from app.adapters.storage.postgres.postgres_schema_migration_store_adapter import (
    PostgresSchemaMigrationStoreAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.storage import ApplyDatabaseMigrationsCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from tests.storage.migration_steps import (
    MIGRATION_NAMES,
    copy_migrations,
    run_migrations,
    workshop_tables,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import build_fixed_wall_clock


def test_edited_applied_migration_is_refused(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    migrations_directory = copy_migrations(tmp_path / "migrations")
    run_migrations(database_url, migrations_directory)
    first_file = migrations_directory / f"{MIGRATION_NAMES[0]}.sql"
    first_file.write_text(
        first_file.read_text(encoding="utf-8") + "\n-- edited\n", encoding="utf-8"
    )

    with pytest.raises(ConflictError, match="changed after it was applied"):
        run_migrations(database_url, migrations_directory)


def test_crlf_checkout_keeps_the_checksum(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    migrations_directory = copy_migrations(tmp_path / "migrations")
    run_migrations(database_url, migrations_directory)
    for file_path in migrations_directory.glob("*.sql"):
        file_path.write_bytes(file_path.read_bytes().replace(b"\n", b"\r\n"))

    report = run_migrations(database_url, migrations_directory)

    assert report.already_applied == MIGRATION_NAMES


def test_failing_migration_is_rolled_back_and_can_be_fixed(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    migrations_directory = copy_migrations(tmp_path / "migrations")
    broken_file = migrations_directory / "9999_broken_step.sql"
    broken_file.write_text(
        "select workshop.create_document_collection('half_done');\nselect 1 / 0;\n",
        encoding="utf-8",
    )

    with pytest.raises(ExternalServiceError, match="9999_broken_step") as error:
        run_migrations(database_url, migrations_directory)

    assert "DivisionByZero" in str(error.value)
    tables = workshop_tables(postgres_server, empty_database_name)
    assert "half_done" not in tables
    assert "users" in tables
    broken_file.write_text(
        "select workshop.create_document_collection('half_done');\n",
        encoding="utf-8",
    )
    report = run_migrations(database_url, migrations_directory)
    assert report.newly_applied == ["9999_broken_step"]
    assert "half_done" in workshop_tables(postgres_server, empty_database_name)


def test_script_session_settings_end_with_the_migration(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    migrations_directory = copy_migrations(tmp_path / "migrations")
    (migrations_directory / "9998_session_setting.sql").write_text(
        "set statement_timeout = '1ms';\nset search_path = workshop;\n",
        encoding="utf-8",
    )
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        ApplyDatabaseMigrationsUseCase(
            migration_source=SqlFileMigrationSourceAdapter(migrations_directory),
            migration_store=PostgresSchemaMigrationStoreAdapter(connection_pool),
            wall_clock=build_fixed_wall_clock(),
        ).run(ApplyDatabaseMigrationsCommand())
        with connection_pool.connection() as connection:
            row = connection.execute(
                "select current_setting('statement_timeout'), "
                "current_setting('search_path')"
            ).fetchone()
    finally:
        connection_pool.close()

    assert row == ("0", '"$user", public')
