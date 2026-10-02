"""
Row-level security settings of one transaction, and storage error translation.

Every collection table has the policy (see migrations/0001):

    business_id = current_setting('app.business_id', true)
    or current_setting('app.bypass_rls', true) = 'on'

The adapter sets both values with `set_config(..., is_local => true)` (the
parameterized form of SET LOCAL) at the start of each transaction, so they
end with it and never leak to the next user of a pooled connection. With no
settings at all a session sees and writes nothing (default deny).
"""

import psycopg
from psycopg import errors as database_errors

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
    """Set the RLS settings of the current transaction for `scope`."""

    if scope.business_id is None:
        connection.execute(
            "select set_config('app.business_id', '', true), "
            "set_config('app.bypass_rls', 'on', true)"
        )
        return

    connection.execute(
        "select set_config('app.business_id', %s, true), "
        "set_config('app.bypass_rls', 'off', true)",
        (str(scope.business_id),),
    )


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
