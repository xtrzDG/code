import secrets
from collections.abc import Generator
from contextlib import contextmanager
from typing import LiteralString

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import TupleRow

from app.adapters.backup.database_facts_reader import (
    APPLICATION_SCHEMA,
    bypass_row_security,
    probe_isolation,
    read_database_facts,
)
from app.adapters.backup.postgres_programs import (
    locate_program,
    program_connection,
    run_program,
)
from app.contracts.backups import ScratchDatabaseAdapterContract
from app.schemas.dto.backups import DatabaseFacts, IsolationProbe, RestoredDatabase
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.backups.booleans import IsScratchDatabaseKept
from app.schemas.typings.backups.constrained_strings import ScratchDatabaseName
from app.schemas.typings.platform.strings import (
    DatabaseUrl,
    LocalDirectoryPath,
    LocalFilePath,
)

APPLICATION_NAME: str = "assistant-workshop-restore-drill"
PRIVILEGED_ROLE_SQL: LiteralString = (
    "select rolsuper or rolbypassrls from pg_roles where rolname = current_user"
)

type Connection = psycopg.Connection[TupleRow]


class PgRestoreScratchDatabaseAdapter(ScratchDatabaseAdapterContract):
    """
    Restores an archive into a new database of a throwaway server
    (RESTORE_CHECK_DATABASE_URL names the server and a role allowed to
    create databases), never into a database the platform uses.

    `pg_restore --single-transaction --exit-on-error` loads it without
    owners or grants (the drill's roles differ from production's). The
    restored database is counted with the RLS bypass, then probed as a
    role bound by row-level security: the restoring role itself, or a
    throwaway NOLOGIN role when the restoring role is a superuser or has
    BYPASSRLS (which row-level security never binds). The scratch database
    and the probe role are dropped afterwards unless the database is kept.
    """

    def __init__(
        self,
        server_url: DatabaseUrl,
        bin_directory: LocalDirectoryPath | None = None,
    ) -> None:
        self._server_url: DatabaseUrl = server_url
        self._bin_directory: LocalDirectoryPath | None = bin_directory

    def restore_and_inspect(
        self,
        archive: LocalFilePath,
        is_kept: IsScratchDatabaseKept,
    ) -> RestoredDatabase:
        pg_restore: str = locate_program("pg_restore", self._bin_directory)
        name = ScratchDatabaseName(f"restore_drill_{secrets.token_hex(6)}")
        self._run_on_server(
            sql.SQL("create database {} template template0").format(
                sql.Identifier(str(name))
            )
        )
        try:
            restore_connection = program_connection(self._server_url, name)
            run_program(
                pg_restore,
                [
                    "--no-owner",
                    "--no-acl",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-password",
                    "--dbname",
                    restore_connection.conninfo,
                    str(archive),
                ],
                restore_connection,
                "pg_restore",
            )
            facts, probes = self._inspect(name)
        finally:
            if not is_kept:
                self._run_on_server(
                    sql.SQL("drop database if exists {} with (force)").format(
                        sql.Identifier(str(name))
                    )
                )

        return RestoredDatabase(
            scratch_database=name, facts=facts, isolation_probes=probes
        )

    def _inspect(
        self, name: ScratchDatabaseName
    ) -> tuple[DatabaseFacts, list[IsolationProbe]]:
        with self._connect(str(name)) as connection:
            bypass_row_security(connection, True)
            facts: DatabaseFacts = read_database_facts(connection)
            with bound_role(connection):
                probes: list[IsolationProbe] = probe_isolation(
                    connection, facts.secured_tables
                )

        return facts, probes

    def _run_on_server(self, statement: sql.Composed) -> None:
        with self._connect(None) as connection:
            connection.execute(statement)

    @contextmanager
    def _connect(self, database_name: str | None) -> Generator[Connection]:
        parameters = dict(conninfo_to_dict(str(self._server_url)))
        if database_name is not None:
            parameters["dbname"] = database_name
        try:
            connection = psycopg.connect(
                make_conninfo("", **parameters),
                autocommit=True,
                application_name=APPLICATION_NAME,
            )
        except psycopg.Error as error:
            raise BackupToolError(
                f"The restore drill's Postgres server could not be reached "
                f"({type(error).__name__})."
            ) from error

        try:
            with connection:
                yield connection
        except psycopg.Error as error:
            raise BackupToolError(
                f"The restore drill's database failed ({type(error).__name__}: "
                f"{error})."
            ) from error


@contextmanager
def bound_role(connection: Connection) -> Generator[None]:
    """
    Make the session a role row-level security binds: the current one, or
    a throwaway NOLOGIN role with read access when the current one skips
    every policy (superuser or BYPASSRLS).
    """

    row = connection.execute(PRIVILEGED_ROLE_SQL).fetchone()
    if row is None or not row[0]:
        yield
        return

    role = sql.Identifier(f"restore_drill_probe_{secrets.token_hex(6)}")
    schema = sql.Identifier(APPLICATION_SCHEMA)
    connection.execute(
        sql.SQL("create role {} nologin nosuperuser nobypassrls").format(role)
    )
    try:
        connection.execute(
            sql.SQL("grant usage on schema {} to {}").format(schema, role)
        )
        connection.execute(
            sql.SQL("grant select on all tables in schema {} to {}").format(
                schema, role
            )
        )
        connection.execute(sql.SQL("set role {}").format(role))
        try:
            yield
        finally:
            connection.execute("reset role")
    finally:
        connection.execute(sql.SQL("drop owned by {}").format(role))
        connection.execute(sql.SQL("drop role {}").format(role))
