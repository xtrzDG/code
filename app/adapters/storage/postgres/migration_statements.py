"""
Running the SQL of one migration file: the whole file in the current
transaction, or a no-transaction file statement by statement.

A no-transaction file (`-- workshop:no-transaction`) exists for `CREATE
INDEX CONCURRENTLY`, which builds an index without blocking writes but
cannot run inside a transaction. When such a build fails (a lock timeout,
a deadlock, a cancelled statement) Postgres keeps the half-built index,
marked INVALID; `IF NOT EXISTS` would then skip it forever, so before each
try every invalid index the file creates is dropped (concurrently) and
built again.
"""

import re

import psycopg
from psycopg import errors, sql
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.clients.postgres.postgres_connection_pool_client import PostgresConnection
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.storage.strings import SchemaMigrationStatement
from app.utilities.storage.sql_statements import code_without_comments

# Errors a later try may not meet again: a lock not granted within
# lock_timeout (55P03) and a lost deadlock (40P01).
RETRYABLE_ERRORS: tuple[type[psycopg.Error], ...] = (
    errors.LockNotAvailable,
    errors.DeadlockDetected,
)
CONCURRENT_INDEX_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*create\s+(?:unique\s+)?index\s+concurrently\s+if\s+not\s+exists\s+"
    r'"?([a-z_][a-z0-9_]*)"?\s',
    re.IGNORECASE,
)
INVALID_INDEXES_QUERY: str = (
    "select c.relname from pg_index i "
    "join pg_class c on c.oid = i.indexrelid "
    "join pg_namespace n on n.oid = c.relnamespace "
    "where n.nspname = %s and c.relname = any(%s) and not i.indisvalid "
    "order by c.relname"
)


def execute_sql(
    connection: PostgresConnection,
    script: SchemaMigrationScript,
    sql_text: str,
) -> None:
    """
    Run SQL text with the simple query protocol (bytes without parameters:
    a file may hold many statements and PL/pgSQL bodies).

    Raises:
        MigrationLockTimeoutError: a lock was not granted in time.
        ExternalServiceError: the SQL failed.
    """

    try:
        connection.execute(sql_text.encode("utf-8"))
    except RETRYABLE_ERRORS as error:
        raise MigrationLockTimeoutError(
            f"Migration {str(script.name)!r} waited too long for a lock and "
            f"was stopped ({type(error).__name__}: {error})."
        ) from error
    except psycopg.Error as error:
        raise ExternalServiceError(
            f"Migration {str(script.name)!r} failed: {type(error).__name__}: {error}"
        ) from error


def concurrent_index_names(
    statements: list[SchemaMigrationStatement],
) -> list[str]:
    """The indexes the statements build concurrently, in file order."""

    names: list[str] = []
    for statement in statements:
        found: re.Match[str] | None = CONCURRENT_INDEX_PATTERN.match(
            code_without_comments(str(statement)) + " "
        )
        if found is not None:
            names.append(found.group(1).lower())

    return names


def drop_invalid_indexes(
    connection: PostgresConnection,
    script: SchemaMigrationScript,
    index_names: list[str],
) -> list[str]:
    """
    Drop (concurrently) the indexes of `index_names` that an earlier try
    left INVALID; returns their names.
    """

    if not index_names:
        return []

    rows: list[TupleRow] = connection.execute(
        INVALID_INDEXES_QUERY, (DOCUMENT_SCHEMA_NAME, index_names)
    ).fetchall()
    invalid: list[str] = [str(row[0]) for row in rows]
    for index_name in invalid:
        statement: sql.Composed = sql.SQL(
            "drop index concurrently if exists {index}"
        ).format(index=sql.Identifier(DOCUMENT_SCHEMA_NAME, index_name))
        execute_sql(connection, script, statement.as_string(connection))

    return invalid
