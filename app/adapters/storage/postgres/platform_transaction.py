"""One platform-wide transaction for statements beyond a single collection."""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg

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

    try:
        with connection_pool.transaction() as connection:
            apply_storage_scope(connection, StorageScope.platform_wide())
            yield connection
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
