"""The migration runner against a real Postgres: idempotent, safe, concurrent."""

import io
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import psycopg
import pytest

from app.adapters.storage.postgres.migrate import main
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
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import (
    FIXED_NANOSECONDS,
    MIGRATIONS_DIRECTORY,
    PROJECT_ROOT_DIRECTORY,
    build_fixed_wall_clock,
)

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


def test_migrations_apply_once_and_then_do_nothing(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)

    first_report = run_migrations(database_url)
    second_report = run_migrations(database_url)

    assert first_report.newly_applied == MIGRATION_NAMES
    assert first_report.already_applied == []
    assert second_report.newly_applied == []
    assert second_report.already_applied == MIGRATION_NAMES
    assert second_report.pending == []
    assert second_report.unknown_applied == []
    with postgres_server.admin_connection(empty_database_name) as connection:
        recorded = connection.execute(
            "select name, length(checksum), applied_at "
            "from workshop.schema_migrations order by name"
        ).fetchall()
    assert recorded == [
        (name, 64, FIXED_NANOSECONDS // 1_000) for name in MIGRATION_NAMES
    ]


def test_migrations_create_every_catalog_collection(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    tables = workshop_tables(postgres_server, database_name)

    assert {str(definition.name) for definition in DOCUMENT_COLLECTIONS} <= tables
    assert "schema_migrations" in tables
    assert {
        "channel_message_receipts",
        "manager_telegram_links",
        "calendar_connections",
        "calendar_authorization_states",
        "calendar_event_links",
    } <= tables


def test_collection_function_is_idempotent_and_validates_names(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    with postgres_server.app_connection(database_name) as connection:
        with connection.transaction():
            connection.execute("select set_config('app.bypass_rls', 'on', true)")
            connection.execute(
                "insert into workshop.users "
                "(document_key, business_id, document, created_at, updated_at) "
                "values ('kept', null, '{}', 1, 1)"
            )
        connection.execute("select workshop.create_document_collection('users')")
        connection.execute(
            "select workshop.create_document_collection('new_collection')"
        )
        with pytest.raises(psycopg.errors.InvalidName):
            connection.execute(
                "select workshop.create_document_collection('Bad; drop table x')"
            )
        with connection.transaction():
            connection.execute("select set_config('app.bypass_rls', 'on', true)")
            kept = connection.execute(
                "select count(*) from workshop.users where document_key = 'kept'"
            ).fetchone()

    assert kept == (1,)
    assert "new_collection" in workshop_tables(postgres_server, database_name)


def test_dry_run_lists_pending_without_applying(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)

    dry_report = run_migrations(database_url, is_dry_run=True)

    assert dry_report.pending == MIGRATION_NAMES
    assert dry_report.newly_applied == []
    assert workshop_tables(postgres_server, empty_database_name) == set()
    run_migrations(database_url)
    assert run_migrations(database_url, is_dry_run=True).pending == []


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
    broken_file = migrations_directory / "0099_broken_step.sql"
    broken_file.write_text(
        "select workshop.create_document_collection('half_done');\nselect 1 / 0;\n",
        encoding="utf-8",
    )

    with pytest.raises(ExternalServiceError, match="0099_broken_step") as error:
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
    assert report.newly_applied == ["0099_broken_step"]
    assert "half_done" in workshop_tables(postgres_server, empty_database_name)


def test_script_session_settings_end_with_the_migration(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    migrations_directory = copy_migrations(tmp_path / "migrations")
    (migrations_directory / "0098_session_setting.sql").write_text(
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


def test_unknown_and_reused_versions(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    run_migrations(database_url)
    older_release = tmp_path / "older"
    older_release.mkdir()
    shutil.copy(
        MIGRATIONS_DIRECTORY / f"{MIGRATION_NAMES[0]}.sql",
        older_release / f"{MIGRATION_NAMES[0]}.sql",
    )

    older_report = run_migrations(database_url, older_release)

    assert older_report.unknown_applied == MIGRATION_NAMES[1:]
    assert older_report.newly_applied == []
    (older_release / "0002_conflicting_name.sql").write_text(
        "select 1;\n", encoding="utf-8"
    )
    with pytest.raises(ConflictError, match="reuses version 0002"):
        run_migrations(database_url, older_release)


def test_concurrent_runners_apply_each_migration_once(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    reports: list[DatabaseMigrationsReport] = []
    errors: list[BaseException] = []
    start = threading.Barrier(4)

    def run_runner() -> None:
        try:
            start.wait()
            reports.append(run_migrations(database_url))
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [threading.Thread(target=run_runner) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    applied_names = sorted(name for report in reports for name in report.newly_applied)
    assert applied_names == MIGRATION_NAMES
    with postgres_server.admin_connection(empty_database_name) as connection:
        row = connection.execute(
            "select count(*) from workshop.schema_migrations"
        ).fetchone()
    assert row == (len(MIGRATION_NAMES),)


def test_main_applies_and_reports(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    output, error_output = io.StringIO(), io.StringIO()

    dry_exit_code = main(
        ["--dry-run"],
        {"DATABASE_URL": database_url},
        output=output,
        error_output=error_output,
    )
    apply_exit_code = main(
        [], {"DATABASE_URL": database_url}, output=output, error_output=error_output
    )

    assert dry_exit_code == 0
    assert apply_exit_code == 0
    assert f"pending  {MIGRATION_NAMES[0]}" in output.getvalue()
    assert f"applied  {MIGRATION_NAMES[0]}" in output.getvalue()
    assert f"{len(MIGRATION_NAMES)} applied now" in output.getvalue()
    assert error_output.getvalue() == ""


def test_main_reports_a_failed_migration(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
    tmp_path: Path,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    migrations_directory = tmp_path / "migrations"
    migrations_directory.mkdir()
    (migrations_directory / "0001_broken.sql").write_text(
        "select * from missing_table;", encoding="utf-8"
    )
    error_output = io.StringIO()

    exit_code = main(
        ["--directory", str(migrations_directory)],
        {"DATABASE_URL": database_url},
        output=io.StringIO(),
        error_output=error_output,
    )

    assert exit_code == 1
    assert "0001_broken" in error_output.getvalue()


def test_module_runs_as_a_command(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    database_url = postgres_server.app_database_url(empty_database_name)
    environment = {**os.environ, "DATABASE_URL": database_url}

    completed = subprocess.run(
        [sys.executable, "-m", "app.adapters.storage.postgres.migrate"],
        cwd=PROJECT_ROOT_DIRECTORY,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr
    assert f"applied  {MIGRATION_NAMES[-1]}" in completed.stdout
