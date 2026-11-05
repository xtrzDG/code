"""
Restoring an archive through its SQL script.

`pg_restore --file=-` writes the archive as SQL and `psql` runs it in one
transaction that stops at the first error. A pg_restore newer than the
server can write settings the server does not know: pg_restore 17 opens
every script with `SET transaction_timeout = 0;`, which Postgres 16 (the
version production runs) refuses, so that line of the preamble is left
out for older servers. Only the preamble is looked at; the rest of the
script (table data included) passes through unchanged.
"""

import contextlib
import os
import shutil
import subprocess  # nosec B404
import tempfile
import threading
from typing import IO

from app.adapters.backup.postgres_programs import (
    PROGRAM_TIMEOUT_SECONDS,
    ProgramConnection,
    last_lines,
)
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.platform.strings import LocalFilePath

# The settings block pg_restore writes before the first object.
PREAMBLE_LINE_LIMIT: int = 40
TRANSACTION_TIMEOUT_LINE: bytes = b"SET transaction_timeout = 0;"
# The first server version that knows transaction_timeout.
TRANSACTION_TIMEOUT_SERVER_VERSION: int = 170000


def restore_through_script(
    pg_restore: str,
    psql: str,
    archive: LocalFilePath,
    connection: ProgramConnection,
    server_version: int,
) -> None:
    """
    Load `archive` into the database of `connection` (a server reporting
    `server_version`, as in `server_version_num`); BackupToolError when
    either program fails or the restore does not finish in time.
    """

    with (
        tempfile.TemporaryFile() as restore_errors,
        tempfile.TemporaryFile() as psql_errors,
    ):
        # Located programs with list arguments: no shell, no interpolation.
        reader = subprocess.Popen(  # nosec B603
            [pg_restore, "--no-owner", "--no-acl", "--file=-", str(archive)],
            stdout=subprocess.PIPE,
            stderr=restore_errors,
        )
        writer = subprocess.Popen(  # nosec B603
            [
                psql,
                "--no-psqlrc",
                "--quiet",
                "--single-transaction",
                "--set",
                "ON_ERROR_STOP=1",
                "--dbname",
                connection.conninfo,
                "--file=-",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=psql_errors,
            env={**os.environ, **connection.environment},
        )
        timed_out = threading.Event()
        watchdog = threading.Timer(
            PROGRAM_TIMEOUT_SECONDS, stop_both, (reader, writer, timed_out)
        )
        watchdog.start()
        psql_stopped_first: bool = False
        try:
            pass_script(
                reader.stdout,
                writer.stdin,
                server_version >= TRANSACTION_TIMEOUT_SERVER_VERSION,
            )
            if reader.wait() != 0:
                # The end of a cut script would commit it: psql never sees it.
                writer.kill()
        except BrokenPipeError:
            # psql stopped at an error; its exit code and message tell why.
            psql_stopped_first = True
            reader.kill()
        finally:
            close_quietly(writer.stdin)
            writer_code: int = writer.wait()
            reader_code: int = reader.wait()
            watchdog.cancel()

        if timed_out.is_set():
            raise BackupToolError("pg_restore did not finish in time.")
        if reader_code != 0 and not psql_stopped_first:
            raise BackupToolError(
                f"pg_restore failed with exit code {reader_code}: "
                + last_lines(read_text(restore_errors))
            )
        if writer_code != 0:
            raise BackupToolError(
                f"psql failed with exit code {writer_code}: "
                + last_lines(read_text(psql_errors))
            )


def pass_script(
    script: IO[bytes] | None,
    target: IO[bytes] | None,
    keeps_transaction_timeout: bool,
) -> None:
    """Copy the script, leaving out an unknown setting of its preamble."""

    if script is None or target is None:
        raise BackupToolError("pg_restore and psql could not be connected.")

    for _ in range(PREAMBLE_LINE_LIMIT):
        line: bytes = script.readline()
        if not line:
            return
        if keeps_transaction_timeout or line.rstrip() != TRANSACTION_TIMEOUT_LINE:
            target.write(line)

    shutil.copyfileobj(script, target)


def stop_both(
    reader: subprocess.Popen[bytes],
    writer: subprocess.Popen[bytes],
    timed_out: threading.Event,
) -> None:
    timed_out.set()
    reader.kill()
    writer.kill()


def close_quietly(stream: IO[bytes] | None) -> None:
    if stream is None:
        return
    with contextlib.suppress(BrokenPipeError):
        stream.close()


def read_text(stream: IO[bytes]) -> str:
    stream.seek(0)
    return stream.read().decode("utf-8", errors="replace")
