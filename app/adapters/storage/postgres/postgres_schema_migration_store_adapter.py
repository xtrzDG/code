import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.storage import SchemaMigrationStoreAdapterContract
from app.schemas.dto.storage import AppliedSchemaMigration, SchemaMigrationScript
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)

SCHEMA_MIGRATIONS_TABLE_NAME: str = "schema_migrations"
# Transaction-level advisory lock that serializes migration runners
# (several app instances may start at once). Any fixed bigint works.
MIGRATION_LOCK_KEY: int = 4_711_202_610_010_001


class PostgresSchemaMigrationStoreAdapter(SchemaMigrationStoreAdapterContract):
    """
    Records applied migrations in `workshop.schema_migrations`.

    Each script runs in its own transaction together with its record: after
    taking an advisory lock, the runner re-checks the record, executes the
    script (simple query protocol, so a file may hold many statements and
    PL/pgSQL bodies) and inserts the record. A failing script leaves nothing
    behind. Scripts must not contain transaction control (BEGIN, COMMIT) or
    statements that cannot run in a transaction (CREATE INDEX CONCURRENTLY).
    """

    def __init__(self, connection_pool: PostgresConnectionPoolClient) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._qualified_table_name: str = (
            f"{DOCUMENT_SCHEMA_NAME}.{SCHEMA_MIGRATIONS_TABLE_NAME}"
        )
        table: sql.Identifier = sql.Identifier(
            DOCUMENT_SCHEMA_NAME, SCHEMA_MIGRATIONS_TABLE_NAME
        )
        self._create_schema_query: sql.Composed = sql.SQL(
            "create schema if not exists {schema}"
        ).format(schema=sql.Identifier(DOCUMENT_SCHEMA_NAME))
        self._create_table_query: sql.Composed = sql.SQL(
            "create table if not exists {table} ("
            "name text primary key, "
            "checksum text not null, "
            "applied_at bigint not null)"
        ).format(table=table)
        self._list_query: sql.Composed = sql.SQL(
            "select name, checksum, applied_at from {table} order by name"
        ).format(table=table)
        self._find_checksum_query: sql.Composed = sql.SQL(
            "select checksum from {table} where name = %s"
        ).format(table=table)
        self._insert_query: sql.Composed = sql.SQL(
            "insert into {table} (name, checksum, applied_at) values (%s, %s, %s)"
        ).format(table=table)

    def list_applied(self) -> list[AppliedSchemaMigration]:
        try:
            with self._connection_pool.transaction() as connection:
                if not self._has_bookkeeping_table(connection):
                    return []

                rows: list[TupleRow] = connection.execute(self._list_query).fetchall()
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not read applied migrations ({type(error).__name__})."
            ) from error

        return [
            AppliedSchemaMigration(
                name=SchemaMigrationName(read_text(row, 0)),
                checksum=SchemaMigrationChecksum(read_text(row, 1)),
                applied_at=Microseconds(read_integer(row, 2)),
            )
            for row in rows
        ]

    def apply_if_pending(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
        try:
            with self._connection_pool.transaction() as connection:
                connection.execute(
                    "select pg_advisory_xact_lock(%s)",
                    (MIGRATION_LOCK_KEY,),
                )
                connection.execute(self._create_schema_query)
                connection.execute(self._create_table_query)
                recorded_row: TupleRow | None = connection.execute(
                    self._find_checksum_query,
                    (str(script.name),),
                ).fetchone()
                if recorded_row is not None:
                    self._require_same_checksum(script, read_text(recorded_row, 0))
                    return False

                self._execute_script(connection, script)
                connection.execute(
                    self._insert_query,
                    (str(script.name), str(script.checksum), int(applied_at)),
                )
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Could not record migration {str(script.name)!r} "
                f"({type(error).__name__})."
            ) from error

        return True

    def _has_bookkeeping_table(self, connection: PostgresConnection) -> bool:
        row: TupleRow | None = connection.execute(
            "select to_regclass(%s) is not null",
            (self._qualified_table_name,),
        ).fetchone()
        return row is not None and row[0] is True

    def _execute_script(
        self,
        connection: PostgresConnection,
        script: SchemaMigrationScript,
    ) -> None:
        try:
            # Bytes without parameters use the simple query protocol, which
            # runs every statement of the file in the current transaction.
            connection.execute(str(script.sql).encode("utf-8"))
            # Session settings a script may have changed end with it.
            connection.execute("reset all")
        except psycopg.Error as error:
            raise ExternalServiceError(
                f"Migration {str(script.name)!r} failed and was rolled back: "
                f"{type(error).__name__}: {error}"
            ) from error

    def _require_same_checksum(
        self,
        script: SchemaMigrationScript,
        recorded_checksum: str,
    ) -> None:
        if recorded_checksum != script.checksum:
            raise ConflictError(
                f"Migration {str(script.name)!r} was applied with another "
                "content; never edit an applied migration, add a new one."
            )


def read_text(row: TupleRow, column_index: int) -> str:
    value: object = row[column_index]
    if not isinstance(value, str):
        raise ExternalServiceError(
            f"Unexpected value in schema_migrations column {column_index}."
        )

    return value


def read_integer(row: TupleRow, column_index: int) -> int:
    value: object = row[column_index]
    if not isinstance(value, int):
        raise ExternalServiceError(
            f"Unexpected value in schema_migrations column {column_index}."
        )

    return value
