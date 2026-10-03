"""
A throwaway Postgres 16 server for storage tests.

`initdb` into a fresh temporary directory, `pg_ctl start` listening only on a
unix socket in that directory (no TCP), stop and delete everything at the
end. Postgres refuses to run as root, so under root the server processes run
as the `postgres` (or `nobody`) system user.

Roles: `workshop_admin` (superuser, creates databases) and `workshop_app`
(LOGIN, neither superuser nor BYPASSRLS: the application role, which owns the
test databases and runs the migrations, so forced RLS binds it).
"""

import os
import pwd
import shutil
import socket
import subprocess
import tempfile
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import TupleRow

from app.schemas.typings.platform.strings import DatabaseUrl

DEFAULT_POSTGRES_BIN_DIRECTORY: Path = Path("/usr/lib/postgresql/16/bin")
ADMIN_ROLE_NAME: str = "workshop_admin"
APP_ROLE_NAME: str = "workshop_app"
REQUIRED_PROGRAMS: tuple[str, ...] = ("initdb", "pg_ctl", "postgres")
UNPRIVILEGED_USER_NAMES: tuple[str, ...] = ("postgres", "nobody")
START_TIMEOUT_SECONDS: int = 60


def postgres_bin_directory() -> Path:
    """Binaries directory; POSTGRES_BIN_DIRECTORY overrides the default."""

    configured_directory: str = os.environ.get("POSTGRES_BIN_DIRECTORY", "")
    if configured_directory.strip() != "":
        return Path(configured_directory)

    return DEFAULT_POSTGRES_BIN_DIRECTORY


def is_postgres_available(bin_directory: Path) -> bool:
    return all((bin_directory / program).is_file() for program in REQUIRED_PROGRAMS)


class ThrowawayPostgresServer:
    def __init__(self, bin_directory: Path) -> None:
        self._bin_directory: Path = bin_directory
        self._root_directory: Path | None = None
        self._port: int = 0
        self._run_as: pwd.struct_passwd | None = None

    @property
    def socket_directory(self) -> Path:
        if self._root_directory is None:
            raise RuntimeError("The test Postgres server is not running.")

        return self._root_directory

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        temporary_parent: str | None = "/tmp" if Path("/tmp").is_dir() else None
        root_directory = Path(
            tempfile.mkdtemp(prefix="workshop-pg-", dir=temporary_parent)
        )
        self._root_directory = root_directory
        if os.geteuid() == 0:
            self._run_as = find_unprivileged_user()
            os.chown(root_directory, self._run_as.pw_uid, self._run_as.pw_gid)

        data_directory: Path = root_directory / "data"
        self._run(
            "initdb",
            "--pgdata",
            str(data_directory),
            "--username",
            ADMIN_ROLE_NAME,
            "--auth",
            "trust",
            "--encoding",
            "UTF8",
            "--no-locale",
            "--no-sync",
            "--no-instructions",
        )
        self._port = find_free_port()
        server_options: str = " ".join(
            (
                "-c listen_addresses=''",
                f"-c unix_socket_directories='{root_directory}'",
                f"-c port={self._port}",
                "-c fsync=off",
                "-c synchronous_commit=off",
                "-c full_page_writes=off",
                "-c max_connections=200",
            )
        )
        self._run(
            "pg_ctl",
            "--pgdata",
            str(data_directory),
            "--log",
            str(root_directory / "server.log"),
            "--wait",
            "--timeout",
            str(START_TIMEOUT_SECONDS),
            "--options",
            server_options,
            "start",
        )
        with self.admin_connection() as connection:
            connection.execute(
                sql.SQL("create role {} login nosuperuser nobypassrls").format(
                    sql.Identifier(APP_ROLE_NAME)
                )
            )

    def stop(self) -> None:
        root_directory: Path | None = self._root_directory
        if root_directory is None:
            return

        try:
            self._run(
                "pg_ctl",
                "--pgdata",
                str(root_directory / "data"),
                "--mode",
                "immediate",
                "--wait",
                "stop",
            )
        finally:
            shutil.rmtree(root_directory, ignore_errors=True)
            self._root_directory = None

    def conninfo(self, database_name: str, role_name: str) -> str:
        return make_conninfo(
            host=str(self.socket_directory),
            port=self._port,
            user=role_name,
            dbname=database_name,
        )

    def app_database_url(self, database_name: str) -> DatabaseUrl:
        return DatabaseUrl(self.conninfo(database_name, APP_ROLE_NAME))

    def admin_connection(
        self,
        database_name: str = "postgres",
    ) -> psycopg.Connection[TupleRow]:
        return psycopg.connect(
            self.conninfo(database_name, ADMIN_ROLE_NAME),
            autocommit=True,
        )

    def app_connection(self, database_name: str) -> psycopg.Connection[TupleRow]:
        return psycopg.connect(
            self.conninfo(database_name, APP_ROLE_NAME),
            autocommit=True,
        )

    def create_database(self, template_name: str | None = None) -> str:
        """A new database owned by the application role; returns its name."""

        database_name: str = f"workshop_{uuid.uuid4().hex[:16]}"
        query: sql.Composed = (
            sql.SQL("create database {} owner {}").format(
                sql.Identifier(database_name),
                sql.Identifier(APP_ROLE_NAME),
            )
            if template_name is None
            else sql.SQL("create database {} owner {} template {}").format(
                sql.Identifier(database_name),
                sql.Identifier(APP_ROLE_NAME),
                sql.Identifier(template_name),
            )
        )
        with self.admin_connection() as connection:
            connection.execute(query)

        return database_name

    def drop_database(self, database_name: str) -> None:
        with self.admin_connection() as connection:
            connection.execute(
                sql.SQL("drop database if exists {} with (force)").format(
                    sql.Identifier(database_name)
                )
            )

    def _run(self, program: str, *arguments: str) -> None:
        command: list[str] = [str(self._bin_directory / program), *arguments]
        if self._run_as is None:
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
        else:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                user=self._run_as.pw_uid,
                group=self._run_as.pw_gid,
                extra_groups=[],
                cwd=str(self.socket_directory),
            )

        if completed.returncode != 0:
            raise RuntimeError(
                f"{program} failed with exit code {completed.returncode}:\n"
                f"{completed.stdout}\n{completed.stderr}"
            )


def find_unprivileged_user() -> pwd.struct_passwd:
    for user_name in UNPRIVILEGED_USER_NAMES:
        try:
            return pwd.getpwnam(user_name)
        except KeyError:
            continue

    raise RuntimeError("No unprivileged user to run the test Postgres server as.")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]

    return port
