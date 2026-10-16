"""An archive's SQL script runs through psql, also into an older server."""

import sys
from pathlib import Path

import pytest

from app.adapters.backup.postgres_programs import ProgramConnection
from app.adapters.backup.restore_script import (
    PREAMBLE_LINE_LIMIT,
    restore_through_script,
)
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.platform.strings import LocalFilePath

POSTGRES_16: int = 160015
POSTGRES_17: int = 170006
PREAMBLE: bytes = (
    b"SET statement_timeout = 0;\n"
    b"SET lock_timeout = 0;\n"
    b"SET idle_in_transaction_session_timeout = 0;\n"
    b"SET transaction_timeout = 0;\n"
    b"SET client_encoding = 'UTF8';\n"
)

# Prints the "archive" as its script; a CUT line stops it with an error.
FAKE_PG_RESTORE: str = """
import sys
script = open(sys.argv[-1], "rb").read()
head, cut, _ = script.partition(b"CUT\\n")
sys.stdout.buffer.write(head)
sys.stdout.flush()
if cut:
    sys.stderr.write("pg_restore: error: could not read from input file\\n")
    sys.exit(1)
"""

# Keeps what it ran and how; EARLY stops at once, FAIL at the end.
FAKE_PSQL: str = """
import os
import sys
output = os.environ["FAKE_PSQL_OUTPUT"]
with open(output + ".args", "w") as arguments:
    arguments.write("\\n".join(sys.argv[1:]) + "\\n" + os.environ.get("PGPASSWORD", ""))
first = sys.stdin.buffer.readline()
if first.startswith(b"EARLY"):
    sys.stderr.write("ERROR:  syntax error at or near EARLY\\n")
    sys.exit(3)
script = first + sys.stdin.buffer.read()
with open(output, "wb") as ran:
    ran.write(script)
if b"FAIL" in script:
    sys.stderr.write("ERROR:  relation broke\\n")
    sys.exit(3)
"""


def fake_program(directory: Path, name: str, source: str) -> str:
    program = directory / name
    program.write_text(f"#!{sys.executable}\n{source}")
    program.chmod(0o755)
    return str(program)


def restore(
    tmp_path: Path, script: bytes, server_version: int
) -> tuple[Path, str, str]:
    archive = tmp_path / "dump.pgc"
    archive.write_bytes(script)
    output = tmp_path / "ran.sql"
    restore_through_script(
        fake_program(tmp_path, "pg_restore", FAKE_PG_RESTORE),
        fake_program(tmp_path, "psql", FAKE_PSQL),
        LocalFilePath(str(archive)),
        ProgramConnection(
            conninfo="host=db dbname=restore_drill_ab12",
            environment={"PGPASSWORD": "s3cret", "FAKE_PSQL_OUTPUT": str(output)},
        ),
        server_version,
    )
    return output, str(archive), (tmp_path / "ran.sql.args").read_text()


def test_an_older_server_gets_the_script_without_the_unknown_setting(
    tmp_path: Path,
) -> None:
    body = b"CREATE TABLE workshop.t (line text);\nCOPY workshop.t (line) FROM stdin;\n"
    # Table data that happens to read like the setting stays as it is.
    data = b"".join(b"row\n" for _ in range(PREAMBLE_LINE_LIMIT))
    data += b"SET transaction_timeout = 0;\n\\.\n"

    output, _, arguments = restore(tmp_path, PREAMBLE + body + data, POSTGRES_16)

    assert output.read_bytes() == (
        PREAMBLE.replace(b"SET transaction_timeout = 0;\n", b"") + body + data
    )
    assert arguments.splitlines() == [
        "--no-psqlrc",
        "--quiet",
        "--single-transaction",
        "--set",
        "ON_ERROR_STOP=1",
        "--dbname",
        "host=db dbname=restore_drill_ab12",
        "--file=-",
        "s3cret",
    ]


def test_a_server_that_knows_the_setting_gets_the_whole_script(
    tmp_path: Path,
) -> None:
    script = PREAMBLE + b"CREATE TABLE workshop.t (line text);\n"

    output, _, _ = restore(tmp_path, script, POSTGRES_17)

    assert output.read_bytes() == script


def test_a_long_script_passes_without_blocking(tmp_path: Path) -> None:
    rows = b"".join(b"%d\tsome row text of the dump\n" % n for n in range(200_000))
    script = PREAMBLE + b"COPY workshop.t (n, line) FROM stdin;\n" + rows + b"\\.\n"

    output, _, _ = restore(tmp_path, script, POSTGRES_17)

    assert output.read_bytes() == script


def test_a_failing_statement_reports_psql_s_error(tmp_path: Path) -> None:
    with pytest.raises(BackupToolError) as raised:
        restore(tmp_path, PREAMBLE + b"FAIL;\n", POSTGRES_16)

    assert str(raised.value) == ("psql failed with exit code 3: ERROR:  relation broke")


def test_psql_stopping_early_is_reported_as_its_error(tmp_path: Path) -> None:
    # More than a pipe holds, so writing after psql left breaks the pipe.
    script = b"EARLY\n" + b"x" * 1_000_000 + b"\n"

    with pytest.raises(BackupToolError) as raised:
        restore(tmp_path, script, POSTGRES_17)

    assert str(raised.value) == (
        "psql failed with exit code 3: ERROR:  syntax error at or near EARLY"
    )


def test_a_cut_archive_is_never_committed(tmp_path: Path) -> None:
    with pytest.raises(BackupToolError) as raised:
        restore(tmp_path, PREAMBLE + b"CREATE TABLE workshop.t ();\nCUT\n", POSTGRES_16)

    assert str(raised.value) == (
        "pg_restore failed with exit code 1: "
        "pg_restore: error: could not read from input file"
    )
    # psql was stopped before the end of its input, which would commit.
    assert not (tmp_path / "ran.sql").exists()
