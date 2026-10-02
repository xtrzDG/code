"""
SQL of keyset pages and aggregations of one document table (migration 1042).

Like `document_lookup_sql`, only declared lookup fields reach this module
(the adapter checks them first) and become column identifiers; every value
is a bind parameter.

A keyset page compares `(sort columns, created_at, row_sequence)` with the
position of the previous page's last row: its sort values, and its first
write (`created_at, row_sequence` of the row its storage key names, so ties
keep the order they were written in, like `list_all`). The row comparison
is not leakproof under row-level security, so the first sort column also
gets a plain bound (`doc_x <= $1`), which is: the index range scan starts
at the position and the row comparison only drops the ties already shown.
When the position's row is gone, its write position is NULL and only the
rest of its ties are skipped.
"""

from psycopg import sql

from app.adapters.storage.postgres.document_lookup_sql import (
    LOOKUP_KEYS_TABLE,
    SqlParameters,
    compose_match,
    compose_range,
    lookup_column_name,
)
from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldExclusion,
    DocumentFilter,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)

WRITE_ORDER_COLUMNS: tuple[sql.SQL, ...] = (
    sql.SQL("created_at"),
    sql.SQL("row_sequence"),
)


def compose_page(
    table: sql.Identifier,
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    query: DocumentPageQuery,
    scoped_business_id: str | None,
) -> tuple[sql.Composed, SqlParameters]:
    """`select document::text` of one keyset page."""

    conditions, parameters = compose_filter(
        collection_name, fields, query.where, scoped_business_id
    )
    columns: list[sql.Identifier] = [
        sql.Identifier(lookup_column_name(field)) for field in query.sort_fields
    ]
    conditions.extend(
        sql.SQL("{column} is not null").format(column=column) for column in columns
    )
    direction: sql.SQL = sql.SQL("desc" if query.is_descending else "asc")
    if query.after is not None:
        bound: sql.SQL = sql.SQL("<=" if query.is_descending else ">=")
        comparison: sql.SQL = sql.SQL("<" if query.is_descending else ">")
        conditions.append(
            sql.SQL("{column} {bound} %s").format(column=columns[0], bound=bound)
        )
        parameters.append(int(query.after.values[0]))
        conditions.append(
            sql.SQL(
                "({columns}, created_at, row_sequence) {comparison} ({values}, "
                "(select page_position.created_at from {table} as page_position "
                "where page_position.document_key = %s), "
                "(select page_position.row_sequence from {table} as page_position "
                "where page_position.document_key = %s))"
            ).format(
                columns=sql.SQL(", ").join(columns),
                comparison=comparison,
                values=sql.SQL(", ").join(sql.SQL("%s") for _ in columns),
                table=table,
            )
        )
        parameters.extend(int(value) for value in query.after.values)
        parameters.extend([str(query.after.document_key)] * 2)

    order: sql.Composable = sql.SQL(", ").join(
        sql.SQL("{column} {direction}").format(column=column, direction=direction)
        for column in [*columns, *WRITE_ORDER_COLUMNS]
    )
    statement: sql.Composed = sql.SQL(
        "select document::text from {table} where {where} order by {order} limit %s"
    ).format(table=table, where=sql.SQL(" and ").join(conditions), order=order)
    parameters.append(int(query.limit))
    return statement, parameters


def compose_aggregation(
    table: sql.Identifier,
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    aggregation: DocumentAggregation,
    scoped_business_id: str | None,
) -> tuple[sql.Composed, SqlParameters]:
    """
    One row per group: the group values, the bucket (0-based), the count,
    then the asked totals and the largest value.
    """

    conditions, where_parameters = compose_filter(
        collection_name, fields, aggregation.where, scoped_business_id
    )
    selected: list[sql.Composable] = [
        sql.Identifier(lookup_column_name(field)) for field in aggregation.group_by
    ]
    select_parameters: SqlParameters = []
    if aggregation.buckets is not None:
        bucket_column = sql.Identifier(lookup_column_name(aggregation.buckets.field))
        starts: list[int] = [int(start) for start in aggregation.buckets.starts]
        selected.append(
            sql.SQL("width_bucket({column}, %s::bigint[]) - 1").format(
                column=bucket_column
            )
        )
        select_parameters.append(starts)
        conditions.append(sql.SQL("{column} >= %s").format(column=bucket_column))
        where_parameters.append(starts[0])

    grouped_count: int = len(selected)
    selected.append(sql.SQL("count(*)"))
    selected.extend(
        sql.SQL("coalesce(sum({column}), 0)::bigint").format(
            column=sql.Identifier(lookup_column_name(field))
        )
        for field in aggregation.totals_of
    )

    if aggregation.latest_of is not None:
        selected.append(
            sql.SQL("max({column})").format(
                column=sql.Identifier(lookup_column_name(aggregation.latest_of))
            )
        )

    statement: sql.Composed = sql.SQL(
        "select {selected} from {table} where {where}"
    ).format(
        selected=sql.SQL(", ").join(selected),
        table=table,
        where=sql.SQL(" and ").join(conditions),
    )
    if grouped_count > 0:
        statement = sql.SQL("{statement} group by {positions}").format(
            statement=statement,
            positions=sql.SQL(", ").join(
                sql.Literal(position) for position in range(1, grouped_count + 1)
            ),
        )

    return statement, [*select_parameters, *where_parameters]


def compose_filter(
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    where: DocumentFilter,
    scoped_business_id: str | None,
) -> tuple[list[sql.Composable], SqlParameters]:
    """The conditions of `where`, plus the business of a business scope."""

    conditions: list[sql.Composable] = [sql.SQL("true")]
    parameters: SqlParameters = []
    if scoped_business_id is not None:
        conditions.append(sql.SQL("business_id = %s"))
        parameters.append(scoped_business_id)

    for match in where.matches:
        condition, match_parameters = compose_match(collection_name, fields, match)
        conditions.append(condition)
        parameters.extend(match_parameters)

    for among in where.among:
        condition, among_parameters = compose_among(collection_name, fields, among)
        conditions.append(condition)
        parameters.extend(among_parameters)

    for exclusion in where.excluding:
        condition, exclusion_parameters = compose_exclusion(exclusion)
        conditions.append(condition)
        parameters.extend(exclusion_parameters)

    for within in where.ranges:
        range_conditions, range_parameters = compose_range(within)
        conditions.extend(range_conditions)
        parameters.extend(range_parameters)

    return conditions, parameters


def compose_among(
    collection_name: DocumentCollectionName,
    fields: dict[DocumentFieldPath, LookupFieldKind],
    among: DocumentFieldAmong,
) -> tuple[sql.Composable, SqlParameters]:
    values: list[str] = [str(value) for value in among.values]
    if fields.get(among.field) is LookupFieldKind.ELEMENT_TEXT:
        condition: sql.Composable = sql.SQL(
            "document_key in (select lookup_key.document_key "
            "from {keys} as lookup_key "
            "where lookup_key.collection_name = %s "
            "and lookup_key.field_path = %s and lookup_key.field_value = any(%s))"
        ).format(keys=LOOKUP_KEYS_TABLE)
        return condition, [str(collection_name), str(among.field), values]

    column: sql.Identifier = sql.Identifier(lookup_column_name(among.field))
    return sql.SQL("{column} = any(%s)").format(column=column), [values]


def compose_exclusion(
    exclusion: DocumentFieldExclusion,
) -> tuple[sql.Composable, SqlParameters]:
    column: sql.Identifier = sql.Identifier(lookup_column_name(exclusion.field))
    return sql.SQL("{column} is distinct from %s").format(column=column), [
        str(exclusion.value)
    ]
