"""
The bookkeeping SQL of the migration runner: `workshop.schema_migrations`,
the runners' lock and the lock timeout of a migration's statements.
"""

from psycopg import sql
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.clients.postgres.postgres_connection_pool_client import PostgresConnection
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds

SCHEMA_MIGRATIONS_TABLE_NAME: str = "schema_migrations"
QUALIFIED_TABLE_NAME: str = f"{DOCUMENT_SCHEMA_NAME}.{SCHEMA_MIGRATIONS_TABLE_NAME}"
# Advisory lock that serializes migration runners (several app instances
# may start at once). Any fixed bigint works; a transactional file takes it
# for its transaction, a no-transaction file for its session.
MIGRATION_LOCK_KEY: int = 4_711_202_610_010_001
TABLE: sql.Identifier = sql.Identifier(
    DOCUMENT_SCHEMA_NAME, SCHEMA_MIGRATIONS_TABLE_NAME
)
CREATE_SCHEMA_QUERY: sql.Composed = sql.SQL(
    "create schema if not exists {schema}"
).format(schema=sql.Identifier(DOCUMENT_SCHEMA_NAME))
CREATE_TABLE_QUERY: sql.Composed = sql.SQL(
    "create table if not exists {table} ("
    "name text primary key, "
    "checksum text not null, "
    "applied_at bigint not null)"
).format(table=TABLE)
LIST_QUERY: sql.Composed = sql.SQL(
    "select name, checksum, applied_at from {table} order by name"
).format(table=TABLE)
FIND_CHECKSUM_QUERY: sql.Composed = sql.SQL(
    "select checksum from {table} where name = %s"
).format(table=TABLE)
INSERT_QUERY: sql.Composed = sql.SQL(
    "insert into {table} (name, checksum, applied_at) values (%s, %s, %s)"
).format(table=TABLE)


def prepare_bookkeeping(connection: PostgresConnection) -> None:
    connection.execute(CREATE_SCHEMA_QUERY)
    connection.execute(CREATE_TABLE_QUERY)


def is_recorded(connection: PostgresConnection, script: SchemaMigrationScript) -> bool:
    """
    True when the script is already recorded (another runner was first).

    Raises:
        ConflictError: it was recorded with another content.
    """

    recorded_row: TupleRow | None = connection.execute(
        FIND_CHECKSUM_QUERY, (str(script.name),)
    ).fetchone()
    if recorded_row is None:
        return False

    if read_text(recorded_row, 0) != script.checksum:
        raise ConflictError(
            f"Migration {str(script.name)!r} was applied with another "
            "content; never edit an applied migration, add a new one."
        )

    return True


def bound_lock_waits(
    connection: PostgresConnection,
    lock_timeout: LockWaitSeconds,
    is_local: bool,
) -> None:
    """
    `lock_timeout` for what follows: the transaction (`is_local`) or the
    session. A statement that waits longer for a lock fails instead of
    queueing the live release's writes behind it.
    """

    connection.execute(
        "select set_config('lock_timeout', %s, %s)",
        (f"{int(lock_timeout)}s", is_local),
    )


def has_bookkeeping_table(connection: PostgresConnection) -> bool:
    row: TupleRow | None = connection.execute(
        "select to_regclass(%s) is not null", (QUALIFIED_TABLE_NAME,)
    ).fetchone()
    return row is not None and row[0] is True


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
