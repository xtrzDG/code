"""
SQL of trigger-kept lookup columns (migration 1122 and later): which
columns a trigger fills, how many rows still miss a value, and one keyset
batch of the backfill.

A trigger-kept column is a plain (not generated) `doc_<field>` column of a
collection table; `workshop.fill_lookup_columns()` fills it from the
document field `<field>` on every insert and on every update of
`document`. The backfill therefore writes `document = document`: the row is
rewritten once and the trigger computes every lookup column of the table,
exactly as a new write would, so the backfill can never disagree with it.
Only rows whose document has the field and whose column is still empty
are written; the rest of the batch is only looked at.
"""

from psycopg import sql

from app.schemas.dto.lookup_backfill import TriggerLookupColumn

TRIGGER_COLUMNS_QUERY: str = (
    "select c.relname, a.attname from pg_attribute a "
    "join pg_class c on c.oid = a.attrelid "
    "join pg_namespace n on n.oid = c.relnamespace "
    "where n.nspname = 'workshop' and c.relkind = 'r' "
    "and a.attname like 'doc\\_%' and a.attgenerated = '' "
    "and a.attnum > 0 and not a.attisdropped "
    "order by c.relname, a.attname"
)
LOOKUP_COLUMN_PREFIX: str = "doc_"


def compose_missing_condition(
    table_alias: str, column: TriggerLookupColumn
) -> sql.Composed:
    """The row has the field in its document but not yet in its column."""

    alias: sql.Identifier = sql.Identifier(table_alias)
    return sql.SQL(
        "{alias}.{column} is null "
        "and {alias}.document -> {field} is not null "
        "and {alias}.document -> {field} <> 'null'::jsonb"
    ).format(
        alias=alias,
        column=sql.Identifier(LOOKUP_COLUMN_PREFIX + str(column.field)),
        field=sql.Literal(str(column.field)),
    )


def compose_count_missing(column: TriggerLookupColumn) -> sql.Composed:
    return sql.SQL("select count(*) from {table} as target where {missing}").format(
        table=sql.Identifier("workshop", str(column.collection_name)),
        missing=compose_missing_condition("target", column),
    )


def compose_fill_batch(column: TriggerLookupColumn) -> sql.Composed:
    """
    Parameters: the key after which the batch starts ('' for the first),
    the batch size. Returns one row: the batch's last key (NULL when no row
    was left), the rows looked at and the rows filled.
    """

    table: sql.Identifier = sql.Identifier("workshop", str(column.collection_name))
    return sql.SQL(
        "with batch as ("
        "select document_key from {table} where document_key > %s "
        "order by document_key limit %s"
        "), filled as ("
        "update {table} as target set document = target.document from batch "
        "where target.document_key = batch.document_key and {missing} "
        "returning 1"
        ") select (select max(document_key) from batch), "
        "(select count(*) from batch), (select count(*) from filled)"
    ).format(table=table, missing=compose_missing_condition("target", column))
