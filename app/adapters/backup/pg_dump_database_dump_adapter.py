import psycopg
from psycopg import IsolationLevel

from app.adapters.backup.database_facts_reader import (
    bypass_row_security,
    read_database_facts,
)
from app.adapters.backup.postgres_programs import (
    locate_program,
    program_connection,
    run_program,
)
from app.contracts.backups import DatabaseDumpAdapterContract
from app.schemas.dto.backups import DatabaseFacts
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.platform.strings import (
    DatabaseUrl,
    LocalDirectoryPath,
    LocalFilePath,
)

APPLICATION_NAME: str = "assistant-workshop-backup"
# pg_dump reads the tables as the application role, which the forced
# row-level security binds too: the application's own bypass switch lets
# it (and only this session) see every business's rows.
DUMP_SESSION_SETTINGS: dict[str, str] = {"app.bypass_rls": "on"}


class PgDumpDatabaseDumpAdapter(DatabaseDumpAdapterContract):
    """
    A consistent custom-format dump (`pg_dump --format=custom`) and the
    facts of exactly the dumped state.

    A read-only REPEATABLE READ transaction exports its snapshot; the rows
    of every table are counted in it and pg_dump dumps the same snapshot
    (`--snapshot`), so the manifest's counts are the archive's counts even
    while the platform keeps writing. Owners and grants stay in the archive
    (a restore may skip them); the password never reaches the command line.
    """

    def __init__(
        self,
        database_url: DatabaseUrl,
        bin_directory: LocalDirectoryPath | None = None,
    ) -> None:
        self._database_url: DatabaseUrl = database_url
        self._bin_directory: LocalDirectoryPath | None = bin_directory

    def dump(self, target: LocalFilePath) -> DatabaseFacts:
        pg_dump: str = locate_program("pg_dump", self._bin_directory)
        try:
            connection = psycopg.connect(
                str(self._database_url), application_name=APPLICATION_NAME
            )
        except psycopg.Error as error:
            raise BackupToolError(
                f"The database could not be reached for the backup "
                f"({type(error).__name__})."
            ) from error

        with connection:
            connection.set_isolation_level(IsolationLevel.REPEATABLE_READ)
            connection.set_read_only(True)
            try:
                snapshot_row = connection.execute(
                    "select pg_export_snapshot()"
                ).fetchone()
                bypass_row_security(connection, True)
                facts: DatabaseFacts = read_database_facts(connection)
            except psycopg.Error as error:
                raise BackupToolError(
                    f"The database could not be counted for the backup "
                    f"({type(error).__name__}: {error})."
                ) from error

            snapshot: str = "" if snapshot_row is None else str(snapshot_row[0])
            dump_connection = program_connection(
                self._database_url, session_settings=DUMP_SESSION_SETTINGS
            )
            run_program(
                pg_dump,
                [
                    "--format=custom",
                    f"--snapshot={snapshot}",
                    "--enable-row-security",
                    "--no-password",
                    f"--file={target}",
                    "--dbname",
                    dump_connection.conninfo,
                ],
                dump_connection,
                "pg_dump",
            )
            connection.rollback()

        return facts
