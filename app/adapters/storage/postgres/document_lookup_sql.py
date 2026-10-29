"""
SQL of the indexed queries of one document table (see migrations/1010).

Only declared lookup fields reach this module (the adapter checks them
first), and they become identifiers: the plain column `business_id`, a
generated column `doc_<field>`, or rows of `workshop.document_lookup_keys`
for list fields. Every value is a bind parameter; nothing a caller passes is
formatted into the SQL text.
"""

from psycopg import sql

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentLookup,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.utilities.storage.document_tenancy import BUSINESS_ID_FIELD_NAME

LOOKUP_KEYS_TABLE: sql.Identifier = sql.Identifier(
    DOCUMENT_SCHEMA_NAME, "document_lookup_keys"
)
GENERATED_COLUMN_PREFIX: str = "doc_"
FIRST_WRITE_ORDER: sql.SQL = sql.SQL("created_at, row_sequence")

type SqlParameters = list[object]


def lookup_column_name(field: DocumentFieldPath) -> str:
    """The plain column of a TEXT or INTEGER lookup field."""

    if str(field) == BUSINESS_ID_FIELD_NAME:
        return BUSINESS_ID_FIELD_NAME

    return f"{GENERATED_COLUMN_PREFIX}{field}"


def compose_select(
    table: sql.Identifier,
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    lookup: DocumentLookup,
    scoped_business_id: str | None,
) -> tuple[sql.Composed, SqlParameters]:
    """`select document::text` of the documents `lookup` returns."""

    where, parameters = compose_where(
        collection_name, fields, lookup, scoped_business_id
    )
    query: sql.Composed = sql.SQL(
        "select document::text from {table} where {where} order by {order}"
    ).format(table=table, where=where, order=compose_order(lookup))
    if lookup.limit is not None:
        query = sql.SQL("{query} limit %s").format(query=query)
        parameters.append(int(lookup.limit))

    return query, parameters


def compose_count(
    table: sql.Identifier,
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    lookup: DocumentLookup,
    scoped_business_id: str | None,
) -> tuple[sql.Composed, SqlParameters]:
    where, parameters = compose_where(
        collection_name, fields, lookup, scoped_business_id
    )
    query: sql.Composed = sql.SQL("select count(*) from {table} where {where}").format(
        table=table, where=where
    )
    return query, parameters


def compose_delete_batch(
    table: sql.Identifier,
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    lookup: DocumentLookup,
    scoped_business_id: str | None,
    batch_size: DocumentQueryLimit,
) -> tuple[sql.Composed, SqlParameters]:
    """Delete at most `batch_size` of the documents `lookup` returns."""

    where, parameters = compose_where(
        collection_name, fields, lookup, scoped_business_id
    )
    query: sql.Composed = sql.SQL(
        "delete from {table} where document_key in ("
        "select document_key from {table} where {where} "
        "order by {order} limit %s)"
    ).format(table=table, where=where, order=compose_order(lookup))
    parameters.append(int(batch_size))
    return query, parameters


def compose_where(
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    lookup: DocumentLookup,
    scoped_business_id: str | None,
) -> tuple[sql.Composed, SqlParameters]:
    """
    The conditions of `lookup`, plus the business of a business scope (the
    explicit filter keeps the business indexes usable).
    """

    conditions: list[sql.Composable] = []
    parameters: SqlParameters = []
    if scoped_business_id is not None:
        conditions.append(sql.SQL("business_id = %s"))
        parameters.append(scoped_business_id)

    for match in lookup.matches:
        condition, match_parameters = compose_match(collection_name, fields, match)
        conditions.append(condition)
        parameters.extend(match_parameters)

    if lookup.within is not None:
        range_conditions, range_parameters = compose_range(lookup.within)
        conditions.extend(range_conditions)
        parameters.extend(range_parameters)

    if not conditions:
        conditions.append(sql.SQL("true"))

    return sql.SQL(" and ").join(conditions), parameters


def compose_match(
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    match: DocumentFieldMatch,
) -> tuple[sql.Composable, SqlParameters]:
    if fields.get(match.field) is LookupFieldKind.ELEMENT_TEXT:
        condition: sql.Composable = sql.SQL(
            "document_key in (select lookup_key.document_key "
            "from {keys} as lookup_key "
            "where lookup_key.collection_name = %s "
            "and lookup_key.field_path = %s and lookup_key.field_value = %s)"
        ).format(keys=LOOKUP_KEYS_TABLE)
        return condition, [str(collection_name), str(match.field), str(match.value)]

    column: sql.Identifier = sql.Identifier(lookup_column_name(match.field))
    return sql.SQL("{column} = %s").format(column=column), [str(match.value)]


def compose_range(
    within: DocumentFieldRange,
) -> tuple[list[sql.Composable], SqlParameters]:
    column: sql.Identifier = sql.Identifier(lookup_column_name(within.field))
    conditions: list[sql.Composable] = []
    parameters: SqlParameters = []
    if within.lower is not None:
        conditions.append(sql.SQL("{column} >= %s").format(column=column))
        parameters.append(int(within.lower))

    if within.upper is not None:
        conditions.append(sql.SQL("{column} < %s").format(column=column))
        parameters.append(int(within.upper))

    return conditions, parameters


def compose_order(lookup: DocumentLookup) -> sql.Composable:
    """
    The field, ties in first-write order in both directions. Postgres puts
    NULL after every value ascending and before them descending, like the
    in-memory collection.
    """

    if lookup.order is None:
        return FIRST_WRITE_ORDER

    column: sql.Identifier = sql.Identifier(lookup_column_name(lookup.order.field))
    direction: sql.SQL = sql.SQL("desc" if lookup.order.is_descending else "asc")
    return sql.SQL("{column} {direction}, {ties}").format(
        column=column, direction=direction, ties=FIRST_WRITE_ORDER
    )
