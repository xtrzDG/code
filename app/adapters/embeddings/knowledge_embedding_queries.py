"""
The statements of `workshop.knowledge_embeddings` (migration 1211). The
pgvector type and operator are qualified with the schema the extension
lives in (`public` when 1211 created it, wherever an administrator put it
otherwise).
"""

from dataclasses import dataclass
from typing import LiteralString

from psycopg import sql

KNOWLEDGE_EMBEDDINGS_TABLE: str = "knowledge_embeddings"
# Where pgvector lives and whether 1211 made the table (any scope may ask:
# both are catalog reads).
READ_AVAILABILITY: LiteralString = (
    "select n.nspname, to_regclass('workshop.knowledge_embeddings') is not null"
    " from pg_catalog.pg_extension e"
    " join pg_catalog.pg_namespace n on n.oid = e.extnamespace"
    " where e.extname = 'vector'"
)
READ_FINGERPRINTS: LiteralString = (
    "select item_id, fingerprint from workshop.knowledge_embeddings"
    " where business_id = %(business_id)s"
)
DELETE_ITEMS: LiteralString = (
    "delete from workshop.knowledge_embeddings"
    " where business_id = %(business_id)s and item_id = any(%(item_ids)s)"
)


@dataclass(frozen=True)
class VectorQueries:
    """The statements that name pgvector's type and operator."""

    upsert: sql.Composed
    nearest: sql.Composed


def build_vector_queries(vector_schema: str) -> VectorQueries:
    """The statements for pgvector installed in `vector_schema`."""

    schema: sql.Identifier = sql.Identifier(vector_schema)
    vector_type: sql.Composed = sql.SQL("{}.vector").format(schema)
    distance: sql.Composed = sql.SQL("operator({}.<=>)").format(schema)
    return VectorQueries(
        upsert=sql.SQL(
            "insert into workshop.knowledge_embeddings"
            " (business_id, item_id, model_id, fingerprint, embedding, updated_at)"
            " values (%(business_id)s, %(item_id)s, %(model_id)s,"
            " %(fingerprint)s, %(embedding)s::{vector}, %(updated_at)s)"
            " on conflict (business_id, item_id) do update set"
            " model_id = excluded.model_id, fingerprint = excluded.fingerprint,"
            " embedding = excluded.embedding, updated_at = excluded.updated_at"
        ).format(vector=vector_type),
        nearest=sql.SQL(
            "select item_id, 1 - (embedding {distance} %(query)s::{vector}),"
            " fingerprint"
            " from workshop.knowledge_embeddings"
            " where business_id = %(business_id)s and model_id = %(model_id)s"
            " and {schema}.vector_dims(embedding) = %(dimensions)s"
            " order by embedding {distance} %(query)s::{vector}, item_id"
            " limit %(limit)s"
        ).format(distance=distance, vector=vector_type, schema=schema),
    )
