"""The SQL statements of one document table, composed once per collection."""

from dataclasses import dataclass

from psycopg import sql

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


@dataclass(frozen=True)
class DocumentTableQueries:
    """
    Statements of `workshop.<collection_name>` (technical record).

    Each read, lock and delete exists twice: platform-wide, and filtered by
    the business of a business scope (so the index on business_id is used).
    Queries by lookup field are composed per call (`document_lookup_sql`).
    """

    table: sql.Identifier
    upsert: sql.Composed
    insert_if_absent: sql.Composed
    get: sql.Composed
    get_in_business: sql.Composed
    lock: sql.Composed
    lock_in_business: sql.Composed
    list_all: sql.Composed
    list_in_business: sql.Composed
    delete: sql.Composed
    delete_in_business: sql.Composed


def build_document_table_queries(
    collection_name: DocumentCollectionName,
) -> DocumentTableQueries:
    table: sql.Identifier = sql.Identifier(DOCUMENT_SCHEMA_NAME, str(collection_name))
    return DocumentTableQueries(
        table=table,
        upsert=sql.SQL(
            "insert into {table} "
            "(document_key, business_id, document, created_at, updated_at) "
            "values (%s, %s, %s::jsonb, %s, %s) "
            "on conflict (document_key) do update set "
            "business_id = excluded.business_id, "
            "document = excluded.document, "
            "updated_at = excluded.updated_at"
        ).format(table=table),
        insert_if_absent=sql.SQL(
            "insert into {table} "
            "(document_key, business_id, document, created_at, updated_at) "
            "values (%s, %s, %s::jsonb, %s, %s) on conflict do nothing"
        ).format(table=table),
        get=sql.SQL(
            "select document::text from {table} where document_key = %s"
        ).format(table=table),
        get_in_business=sql.SQL(
            "select document::text from {table} "
            "where document_key = %s and business_id = %s"
        ).format(table=table),
        lock=sql.SQL(
            "select document::text from {table} where document_key = %s for update"
        ).format(table=table),
        lock_in_business=sql.SQL(
            "select document::text from {table} "
            "where document_key = %s and business_id = %s for update"
        ).format(table=table),
        list_all=sql.SQL(
            "select document::text from {table} order by created_at, row_sequence"
        ).format(table=table),
        list_in_business=sql.SQL(
            "select document::text from {table} where business_id = %s "
            "order by created_at, row_sequence"
        ).format(table=table),
        delete=sql.SQL("delete from {table} where document_key = %s").format(
            table=table
        ),
        delete_in_business=sql.SQL(
            "delete from {table} where document_key = %s and business_id = %s"
        ).format(table=table),
    )
