"""
Row-level security settings of one transaction, and storage error translation.

Every table has, besides the owner's, two policies (migration 1200):

    tenant_isolation  to workshop_tenant:
        business_id = current_setting('app.business_id', true)
    platform_access   to workshop_platform: every row

The adapter sets `app.business_id` with `set_config(..., is_local => true)`
(the parameterized form of SET LOCAL) at the start of each transaction, in
the same round trip as its `begin` (or its savepoint inside a unit of
work), so it ends with it and never leaks to the next user of a pooled
connection. On a tenant connection a business scope sees that business's
rows; the platform and unscoped scopes name no business and see nothing
(default deny), whatever else a session sets: there is no setting that
widens what the tenant role sees. Platform-wide work borrows from the
platform pool, whose role sees every row (`PostgresConnectionPools`).
"""

import psycopg
from psycopg import errors as database_errors
from psycopg import sql

from app.clients.postgres.postgres_connection_pool_client import PostgresConnection
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError

DOCUMENT_SCHEMA_NAME: str = "workshop"
MIGRATION_COMMAND: str = "uv run python -m app.gateways.cli.migrate"
ROW_LEVEL_SECURITY_MARKER: str = "row-level security"


def apply_storage_scope(connection: PostgresConnection, scope: StorageScope) -> None:
    """
    Set the RLS setting of the current transaction for `scope`: the
    business of a business scope, no business otherwise.
    """

    connection.execute(
        "select set_config('app.business_id', %s, true)",
        (business_setting(scope),),
    )


def begin_in_scope(connection: PostgresConnection, scope: StorageScope) -> None:
    """
    Begin a transaction and set its RLS setting for `scope` in one round
    trip: the setting travels as a literal (quoted by libpq, and a business
    id is a validated typed id), so `begin` and the `set_config` select go
    as one simple-protocol message, ahead of every statement of the
    transaction. The caller ends the transaction.
    """

    connection.execute(sql.SQL("begin; {}").format(scope_settings(scope)))


def savepoint_in_scope(
    connection: PostgresConnection, scope: StorageScope, savepoint: sql.Identifier
) -> None:
    """
    Inside an open transaction: set a savepoint and the RLS setting for
    `scope` in one round trip, as `begin_in_scope` does for a transaction.
    Rolled back to, the savepoint restores the setting before it.
    """

    connection.execute(
        sql.SQL("savepoint {}; {}").format(savepoint, scope_settings(scope))
    )


def scope_settings(scope: StorageScope) -> sql.Composed:
    """The `set_config` select of `scope`, its value as a quoted literal."""

    return sql.SQL("select set_config('app.business_id', {}, true)").format(
        sql.Literal(business_setting(scope))
    )


def business_setting(scope: StorageScope) -> str:
    """`app.business_id` of `scope`: its business, or none (empty)."""

    return "" if scope.business_id is None else str(scope.business_id)


def translate_storage_error(
    error: psycopg.Error,
    collection_name: str,
) -> ApplicationError | None:
    """
    The application error for a database failure, or None to re-raise as is.

    - a row-level security violation (writing a row of another business in a
      business scope) -> AccessDeniedError;
    - text Postgres cannot store (the NUL character in JSONB) ->
      ValidationFailedError;
    - a missing schema or table -> ExternalServiceError that names the
      migration command;
    - a role without privileges on the table -> ExternalServiceError (a
      deployment mistake: grant the application role access);
    - connection loss, timeouts, deadlocks (OperationalError) ->
      ExternalServiceError.

    Other errors are programming errors and propagate unchanged.
    """

    if isinstance(error, database_errors.InsufficientPrivilege):
        if ROW_LEVEL_SECURITY_MARKER in str(error):
            return AccessDeniedError(
                f"The document in {collection_name!r} belongs to another "
                "business than the current storage scope."
            )

        return ExternalServiceError(
            f"The database role may not use collection {collection_name!r}; "
            f"grant it usage on schema {DOCUMENT_SCHEMA_NAME} and "
            "select, insert, update, delete on its tables."
        )

    if isinstance(
        error,
        database_errors.UntranslatableCharacter
        | database_errors.CharacterNotInRepertoire,
    ):
        return ValidationFailedError(
            f"A document in {collection_name!r} contains text Postgres cannot "
            "store (the NUL character); strip it at the input boundary."
        )

    if isinstance(
        error,
        database_errors.UndefinedTable | database_errors.InvalidSchemaName,
    ):
        return ExternalServiceError(
            f"Document collection {collection_name!r} has no table yet; "
            f"apply the migrations ({MIGRATION_COMMAND})."
        )

    if isinstance(error, psycopg.OperationalError):
        return ExternalServiceError(
            f"The database failed while using {collection_name!r} "
            f"({type(error).__name__})."
        )

    return None
