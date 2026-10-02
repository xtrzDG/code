"""Statements of `migrate-documents`: walk a table's outdated rows, rewrite each."""

from dataclasses import dataclass

from psycopg import sql

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

# Before every row: created_at is a UNIX time, row_sequence an identity.
FIRST_POSITION: tuple[int, int] = (-1, -1)


@dataclass(frozen=True)
class StoredDocumentUpgradeQueries:
    """
    `select_batch` returns rows whose stored `schema_version` (missing means
    "1") differs from the current one, after a keyset position on the
    `(created_at, row_sequence)` index every table has; `rewrite` replaces a
    row's document only if it is still what was read (technical record).
    """

    select_batch: sql.Composed
    rewrite: sql.Composed


def build_stored_document_upgrade_queries(
    collection_name: DocumentCollectionName,
) -> StoredDocumentUpgradeQueries:
    table: sql.Identifier = sql.Identifier(DOCUMENT_SCHEMA_NAME, str(collection_name))
    return StoredDocumentUpgradeQueries(
        select_batch=sql.SQL(
            "select document_key, document::text, created_at, row_sequence "
            "from {table} "
            "where (created_at, row_sequence) > "
            "(%(after_created_at)s, %(after_row_sequence)s) "
            "and coalesce(document ->> 'schema_version', '1') "
            "<> %(current_version)s "
            "order by created_at, row_sequence "
            "limit %(batch_size)s"
        ).format(table=table),
        rewrite=sql.SQL(
            "update {table} set document = %(upgraded)s::jsonb "
            "where document_key = %(document_key)s "
            "and document = %(stored)s::jsonb"
        ).format(table=table),
    )
