"""The migration runner against a real Postgres: idempotent and concurrent."""

import shutil
import threading
from pathlib import Path

import psycopg
import pytest

from app.schemas.dto.storage import DatabaseMigrationsReport
from app.schemas.exceptions.application_errors import ConflictError
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.migration_steps import (
    MIGRATION_NAMES,
    run_migrations,
    workshop_tables,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import FIXED_NANOSECONDS, MIGRATIONS_DIRECTORY


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
