"""
A custom-format archive restores into a real Postgres 16 server, even
when the pg_restore is newer and opens its script with a setting the
server does not know (pg_restore 17's `SET transaction_timeout = 0;`).
"""

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.backup.postgres_programs import ProgramConnection
from app.adapters.backup.restore_script import restore_through_script
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.platform.strings import LocalFilePath
from tests.storage.postgres_server import (
    ADMIN_ROLE_NAME,
    ThrowawayPostgresServer,
    postgres_bin_directory,
)

POSTGRES_16: int = 160000
POSTGRES_17: int = 170000

# pg_restore as version 17 writes it: the setting right after the first SET.
NEWER_PG_RESTORE: str = """
import subprocess
import sys
script = subprocess.run(
    [{real!r}, *sys.argv[1:]], check=True, capture_output=True
).stdout
head, separator, rest = script.partition(b"SET ")
sys.stdout.buffer.write(head + b"SET transaction_timeout = 0;\\n" + separator + rest)
"""


def dumped_archive(server: ThrowawayPostgresServer, directory: Path) -> Path:
    source: str = server.create_database()
    with server.admin_connection(source) as connection:
        connection.execute("create table drill_rows (n integer primary key, line text)")
        connection.execute(
            "insert into drill_rows "
            "select n, 'row ' || n from generate_series(1, 500) n"
        )
    archive = directory / "dump.pgc"
    subprocess.run(
        [
            str(postgres_bin_directory() / "pg_dump"),
            "--format=custom",
            "--file",
            str(archive),
            server.conninfo(source, ADMIN_ROLE_NAME),
        ],
        check=True,
    )
    return archive


def newer_pg_restore(directory: Path) -> str:
    program = directory / "pg_restore"
    real: str = str(postgres_bin_directory() / "pg_restore")
    program.write_text(f"#!{sys.executable}\n" + NEWER_PG_RESTORE.format(real=real))
    program.chmod(0o755)
    return str(program)


def restore_with_newer_pg_restore(
    server: ThrowawayPostgresServer, tmp_path: Path, server_version: int
) -> str:
    archive = dumped_archive(server, tmp_path)
    target: str = server.create_database()
    restore_through_script(
        newer_pg_restore(tmp_path),
        str(postgres_bin_directory() / "psql"),
        LocalFilePath(str(archive)),
        ProgramConnection(
            conninfo=server.conninfo(target, ADMIN_ROLE_NAME), environment={}
        ),
        server_version,
    )
    return target


def test_a_newer_pg_restore_loads_into_postgres_16(
    postgres_server: ThrowawayPostgresServer, tmp_path: Path
) -> None:
    target: str = restore_with_newer_pg_restore(postgres_server, tmp_path, POSTGRES_16)

    with postgres_server.admin_connection(target) as connection:
        row = connection.execute(
            "select count(*), max(line) from drill_rows"
        ).fetchone()
    assert row == (500, "row 99")


def test_without_leaving_the_setting_out_postgres_16_refuses_it(
    postgres_server: ThrowawayPostgresServer, tmp_path: Path
) -> None:
    with pytest.raises(BackupToolError) as raised:
        restore_with_newer_pg_restore(postgres_server, tmp_path, POSTGRES_17)

    assert 'unrecognized configuration parameter "transaction_timeout"' in str(
        raised.value
    )
