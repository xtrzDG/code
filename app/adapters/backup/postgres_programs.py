"""
The Postgres client programs the backup runs (pg_dump, pg_restore).

They come from POSTGRES_CLIENT_BIN_DIRECTORY when it is set, else from the
PATH (the image installs Debian's postgresql-client). The connection is
given as a conninfo string without the password, which goes in PGPASSWORD,
so no credential appears in the process list. Errors keep the program's
last lines of stderr: Postgres messages name objects, never row contents.
"""

import os
import shutil
import subprocess  # nosec B404 - runs the Postgres client programs, no shell
from dataclasses import dataclass
from pathlib import Path

from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.backups.constrained_strings import ScratchDatabaseName
from app.schemas.typings.platform.strings import DatabaseUrl, LocalDirectoryPath

ERROR_LINES_KEPT: int = 6
ERROR_TEXT_LIMIT: int = 800
# A dump or restore of a big database takes long; one that hangs does not.
PROGRAM_TIMEOUT_SECONDS: int = 6 * 60 * 60


@dataclass(frozen=True)
class ProgramConnection:
    """How a client program reaches a database: its conninfo and environment."""

    conninfo: str
    environment: dict[str, str]


def program_connection(
    database_url: DatabaseUrl,
    database_name: ScratchDatabaseName | None = None,
    session_settings: dict[str, str] | None = None,
) -> ProgramConnection:
    """
    The conninfo of `database_url` (another database of the same server
    when `database_name` is given) with the password moved to PGPASSWORD
    and `session_settings` passed as PGOPTIONS (`-c name=value`).
    """

    parameters: dict[str, str | int | None] = dict(conninfo_to_dict(str(database_url)))
    password = parameters.pop("password", None)
    if database_name is not None:
        parameters["dbname"] = str(database_name)

    environment: dict[str, str] = {}
    if password is not None:
        environment["PGPASSWORD"] = str(password)
    if session_settings:
        environment["PGOPTIONS"] = " ".join(
            f"-c {name}={value}" for name, value in session_settings.items()
        )

    return ProgramConnection(
        conninfo=make_conninfo(
            "", **{name: value for name, value in parameters.items() if value}
        ),
        environment=environment,
    )


def locate_program(name: str, bin_directory: LocalDirectoryPath | None) -> str:
    """The absolute path of a client program, or BackupToolError."""

    search_path: str | None = None if bin_directory is None else str(bin_directory)
    found: str | None = shutil.which(name, path=search_path)
    if found is None:
        raise BackupToolError(
            f"{name} was not found"
            + ("" if bin_directory is None else f" in {bin_directory}")
            + "; install the Postgres client (postgresql-client) or set "
            "POSTGRES_CLIENT_BIN_DIRECTORY."
        )

    return str(Path(found).resolve())


def run_program(
    program: str,
    arguments: list[str],
    connection: ProgramConnection,
    step: str,
) -> None:
    """Run the program to completion; BackupToolError when it fails."""

    try:
        completed = subprocess.run(  # nosec B603 - fixed program, list arguments
            [program, *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROGRAM_TIMEOUT_SECONDS,
            env={**os.environ, **connection.environment},
        )
    except subprocess.TimeoutExpired as error:
        raise BackupToolError(f"{step} did not finish in time.") from error

    if completed.returncode != 0:
        raise BackupToolError(
            f"{step} failed with exit code {completed.returncode}: "
            + last_lines(completed.stderr)
        )


def last_lines(text: str) -> str:
    lines: list[str] = [line for line in text.strip().splitlines() if line.strip()]
    kept: str = " | ".join(lines[-ERROR_LINES_KEPT:])
    return kept[-ERROR_TEXT_LIMIT:] if kept else "no error output"
