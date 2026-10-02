"""The migrate command against a real Postgres: applies, reports, runs as a module."""

import io
import os
import subprocess
import sys
from pathlib import Path

from app.adapters.storage.postgres.migrate import main
from tests.storage.migration_steps import MIGRATION_NAMES
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY


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
