"""Raw rows of the notes table (`knowledge_items`), below the collections."""

import json
from typing import LiteralString

from psycopg import sql

from app.adapters.storage.document_upgrades import StoredJsonObject
from app.adapters.storage.persisted_document_codec import parse_stored_object
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.storage.evolution_documents import NOTES_TABLE

NOTES: sql.Identifier = sql.Identifier("workshop", NOTES_TABLE)
BYPASS_RLS: LiteralString = "select set_config('app.bypass_rls', 'on', true)"


def read_stored(
    connection_pool: PostgresConnectionPoolClient,
    document_key: str,
) -> StoredJsonObject:
    with connection_pool.transaction() as connection:
        connection.execute(BYPASS_RLS)
        row = connection.execute(
            sql.SQL("select document::text from {} where document_key = %s").format(
                NOTES
            ),
            (document_key,),
        ).fetchone()

    assert row is not None
    return parse_stored_object(str(row[0]))


def read_updated_at(
    connection_pool: PostgresConnectionPoolClient,
    document_key: str,
) -> int:
    with connection_pool.transaction() as connection:
        connection.execute(BYPASS_RLS)
        row = connection.execute(
            sql.SQL("select updated_at from {} where document_key = %s").format(NOTES),
            (document_key,),
        ).fetchone()

    assert row is not None and isinstance(row[0], int)
    return row[0]


def write_stored(
    connection_pool: PostgresConnectionPoolClient,
    document_key: str,
    business_id: BusinessId,
    document: StoredJsonObject,
    written_at: int = 1,
) -> None:
    """Insert or replace one row as an older or newer release left it."""

    with connection_pool.transaction() as connection:
        connection.execute(BYPASS_RLS)
        connection.execute(
            sql.SQL(
                "insert into {} (document_key, business_id, document, created_at, "
                "updated_at) values (%s, %s, %s::jsonb, %s, %s) "
                "on conflict (document_key) do update set document = excluded.document"
            ).format(NOTES),
            (
                document_key,
                str(business_id),
                json.dumps(document),
                written_at,
                written_at,
            ),
        )
