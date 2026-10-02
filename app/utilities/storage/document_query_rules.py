"""
Which keyset pages and aggregations a collection accepts: the same checks
on every storage, so a query without its index fails in in-memory tests.

Pages and aggregations run inside one business (or group a bounded range
platform-wide): their rows are selected by an index of the business, a
range, or the sort order, and FILTER_TEXT fields and exclusions only
narrow those rows. A page reads at most `limit` documents; an aggregation
reads none (the database counts), so counting every row of a business is
fine where listing them would not be.
"""

from collections.abc import Mapping

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.storage.document_lookup_fields import (
    MATCH_KINDS,
    RANGE_KINDS,
    SELECTIVE_MATCH_KINDS,
    require_lookup_field,
)

COLUMN_TEXT_KINDS: frozenset[LookupFieldKind] = frozenset(
    {LookupFieldKind.TEXT, LookupFieldKind.FILTER_TEXT}
)


def require_valid_page(
    fields: Mapping[DocumentFieldPath, LookupFieldKind],
    query: DocumentPageQuery,
    collection_label: str,
) -> None:
    """UndeclaredLookupFieldError unless the sort fields are INTEGER fields
    and the filter is valid (the sort order's index selects the rows)."""

    for field in query.sort_fields:
        require_lookup_field(fields, field, RANGE_KINDS, collection_label)

    require_valid_filter(fields, query.where, collection_label, is_ordered=True)


def require_valid_aggregation(
    fields: Mapping[DocumentFieldPath, LookupFieldKind],
    aggregation: DocumentAggregation,
    collection_label: str,
) -> None:
    """
    UndeclaredLookupFieldError unless the filter is valid, the groups are
    TEXT or FILTER_TEXT fields (columns), and the buckets, totals and
    largest value are INTEGER fields.
    """

    require_valid_filter(fields, aggregation.where, collection_label, is_ordered=False)
    for field in aggregation.group_by:
        require_lookup_field(fields, field, COLUMN_TEXT_KINDS, collection_label)

    for integer_field in (
        None if aggregation.buckets is None else aggregation.buckets.field,
        *aggregation.totals_of,
        aggregation.latest_of,
    ):
        if integer_field is not None:
            require_lookup_field(fields, integer_field, RANGE_KINDS, collection_label)


def require_valid_filter(
    fields: Mapping[DocumentFieldPath, LookupFieldKind],
    where: DocumentFilter,
    collection_label: str,
    is_ordered: bool,
) -> None:
    """
    Matches and `among` are TEXT, FILTER_TEXT or ELEMENT_TEXT fields,
    exclusions TEXT or FILTER_TEXT fields, ranges INTEGER fields; FILTER_TEXT
    fields and exclusions need an indexed match (`business_id` counts), a
    range or an index order that selects the rows they narrow.
    """

    matched_fields: list[DocumentFieldPath] = [
        *(match.field for match in where.matches),
        *(among.field for among in where.among),
    ]
    kinds: list[LookupFieldKind] = [
        require_lookup_field(fields, field, MATCH_KINDS, collection_label)
        for field in matched_fields
    ]
    for exclusion in where.excluding:
        require_lookup_field(
            fields, exclusion.field, COLUMN_TEXT_KINDS, collection_label
        )

    for within in where.ranges:
        require_lookup_field(fields, within.field, RANGE_KINDS, collection_label)

    is_narrowing: bool = (
        LookupFieldKind.FILTER_TEXT in kinds or len(where.excluding) > 0
    )
    is_selected_by_index: bool = (
        is_ordered
        or len(where.ranges) > 0
        or any(kind in SELECTIVE_MATCH_KINDS for kind in kinds)
    )
    if is_narrowing and not is_selected_by_index:
        raise UndeclaredLookupFieldError(
            f"Filter fields of {collection_label} only narrow a query by an "
            "indexed lookup field; add one."
        )
