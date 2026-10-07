"""
One platform-wide transaction (or one self-scoped statement) beyond a
single collection.
"""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg
from psycopg import pq

from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
    translate_storage_error,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import ExternalServiceError


@contextmanager
def platform_transaction(
    connection_pool: PostgresConnectionPoolClient,
    collection_name: str,
) -> Generator[PostgresConnection]:
    """
    A transaction that sees every business (`app.bypass_rls = on`, as for
    platform collections). Database failures become application errors the
    same way as in the document collections.
    """

    with (
        storage_errors_translated(collection_name),
        connection_pool.transaction() as connection,
    ):
        apply_storage_scope(connection, StorageScope.platform_wide())
        yield connection


@contextmanager
def platform_statement(
    connection_pool: PostgresConnectionPoolClient,
    collection_name: str,
) -> Generator[PostgresConnection]:
    """
    A connection for one statement that sets its own platform scope (a
    database function that turns `app.bypass_rls` on for its statements),
    without a transaction block: on the pool's autocommit connections the
    statement is a transaction of its own that commits as it ends, so its
    row locks last only while it runs. Inside a pinned connection's open
    transaction (a unit of work) it is a savepoint of that transaction, so
    its error rolls back only itself, as with `platform_transaction`.
    Errors translate as in `platform_transaction`.
    """

    with (
        storage_errors_translated(collection_name),
        connection_pool.connection() as connection,
    ):
        if connection.info.transaction_status is pq.TransactionStatus.IDLE:
            yield connection
            return

        with connection.transaction():
            yield connection


@contextmanager
def storage_errors_translated(collection_name: str) -> Generator[None]:
    """Database failures of the block as application errors (or re-raised)."""

    try:
        yield
    except psycopg.Error as error:
        application_error = translate_storage_error(error, collection_name)
        if application_error is None:
            raise

        raise application_error from error


def read_document_text(row: tuple[object, ...], collection_name: str) -> str:
    """The JSONB document of a `select document::text` row."""

    document_text: object = row[0]
    if not isinstance(document_text, str):
        raise ExternalServiceError(
            f"Collection {collection_name!r} returned a document that is not "
            f"JSON text ({type(document_text).__name__})."
        )

    return document_text
