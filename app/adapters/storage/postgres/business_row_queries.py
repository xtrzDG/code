"""
The SQL of a business's rows across the tables of the application schema:
every base table with a `business_id` column (each document collection, and
the side tables such as `knowledge_embeddings` and
`document_lookup_keys`). Shared by the hard delete (the platform pool) and
the restore drill, which applies the deletion ledger to a restored
database. Table names come from the database's own catalog and are quoted
as identifiers; values are parameters.
"""

from collections.abc import Sequence
from typing import LiteralString

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

APPLICATION_SCHEMA: str = "workshop"
BUSINESS_COLUMN: str = "business_id"
BUSINESS_TABLES_SQL: LiteralString = (
    "select c.table_name from information_schema.columns c"
    " join information_schema.tables t"
    " on t.table_schema = c.table_schema and t.table_name = c.table_name"
    " where c.table_schema = %s and c.column_name = %s"
    " and t.table_type = 'BASE TABLE' order by c.table_name"
)

type Connection = psycopg.Connection[TupleRow]


def list_business_tables(connection: Connection) -> list[str]:
    """The schema's base tables that have a business column, by name."""

    rows = connection.execute(
        BUSINESS_TABLES_SQL, [APPLICATION_SCHEMA, BUSINESS_COLUMN]
    ).fetchall()
    return [str(row[0]) for row in rows]


def count_business_rows(
    connection: Connection, table: str, business_ids: Sequence[str]
) -> int:
    """How many rows of `table` belong to any of the businesses."""

    row = connection.execute(
        sql.SQL("select count(*) from {}.{} where business_id = any(%s)").format(
            sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(table)
        ),
        [list(business_ids)],
    ).fetchone()
    return 0 if row is None else int(row[0])


def delete_business_batch(
    connection: Connection, table: str, business_ids: Sequence[str], limit: int
) -> int:
    """
    Delete at most `limit` rows of the businesses from `table` (by their
    physical row, so any table works, whatever its key); how many went.
    """

    target = sql.SQL("{}.{}").format(
        sql.Identifier(APPLICATION_SCHEMA), sql.Identifier(table)
    )
    cursor = connection.execute(
        sql.SQL(
            "delete from {} where ctid = any(array("
            "select ctid from {} where business_id = any(%s) limit %s))"
        ).format(target, target),
        [list(business_ids), limit],
    )
    return max(cursor.rowcount, 0)
