"""How pg_dump and pg_restore are found, connected and run."""

import sys
from pathlib import Path

import pytest
from psycopg.conninfo import conninfo_to_dict

from app.adapters.backup import postgres_programs
from app.adapters.backup.postgres_programs import (
    ProgramConnection,
    locate_program,
    program_connection,
    run_program,
)
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.backups.constrained_strings import ScratchDatabaseName
from app.schemas.typings.platform.strings import DatabaseUrl, LocalDirectoryPath

NO_CONNECTION: ProgramConnection = ProgramConnection(conninfo="", environment={})


def test_the_password_leaves_the_conninfo_for_the_environment() -> None:
    connection = program_connection(
        DatabaseUrl("postgresql://workshop:s3cret@db.internal:5433/workshop"),
        ScratchDatabaseName("restore_drill_ab12"),
        {"app.bypass_rls": "on"},
    )

    assert "s3cret" not in connection.conninfo
    assert conninfo_to_dict(connection.conninfo) == {
        "host": "db.internal",
        "port": "5433",
        "user": "workshop",
        "dbname": "restore_drill_ab12",
    }
    assert connection.environment == {
        "PGPASSWORD": "s3cret",
        "PGOPTIONS": "-c app.bypass_rls=on",
    }


def test_a_missing_program_names_where_it_was_looked_for(tmp_path: Path) -> None:
    with pytest.raises(BackupToolError) as raised:
        locate_program("pg_dump", LocalDirectoryPath(str(tmp_path)))

    assert str(raised.value) == (
        f"pg_dump was not found in {tmp_path}; install the Postgres client "
        "(postgresql-client) or set POSTGRES_CLIENT_BIN_DIRECTORY."
    )


def test_a_program_in_the_directory_is_found_by_its_real_path(
    tmp_path: Path,
) -> None:
    program = tmp_path / "pg_restore"
    program.write_text("#!/bin/sh\n")
    program.chmod(0o755)

    assert locate_program("pg_restore", LocalDirectoryPath(str(tmp_path))) == str(
        program.resolve()
    )


def python_program(source: str) -> list[str]:
    return ["-c", source]


def test_a_failing_program_reports_its_last_error_lines() -> None:
    script = (
        "import sys\n"
        "sys.stderr.write('\\n'.join(f'line {n}' for n in range(9)) + '\\n')\n"
        "sys.exit(3)\n"
    )

    with pytest.raises(BackupToolError) as raised:
        run_program(sys.executable, python_program(script), NO_CONNECTION, "pg_dump")

    assert str(raised.value) == (
        "pg_dump failed with exit code 3: "
        "line 3 | line 4 | line 5 | line 6 | line 7 | line 8"
    )


def test_a_silent_failure_says_so() -> None:
    with pytest.raises(BackupToolError, match="exit code 2: no error output"):
        run_program(
            sys.executable,
            python_program("import sys; sys.exit(2)"),
            NO_CONNECTION,
            "pg_restore",
        )


def test_a_program_that_hangs_is_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(postgres_programs, "PROGRAM_TIMEOUT_SECONDS", 0.2)

    with pytest.raises(BackupToolError, match="pg_restore did not finish in time"):
        run_program(
            sys.executable,
            python_program("import time; time.sleep(10)"),
            NO_CONNECTION,
            "pg_restore",
        )


def test_the_program_gets_the_connection_environment() -> None:
    script = "import os, sys; sys.exit(0 if os.environ['PGPASSWORD'] == 'pw' else 4)"

    run_program(
        sys.executable,
        python_program(script),
        ProgramConnection(conninfo="", environment={"PGPASSWORD": "pw"}),
        "pg_dump",
    )
