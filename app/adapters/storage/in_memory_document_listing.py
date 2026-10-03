"""
Keyset pages and aggregations evaluated on stored JSON in memory, with the
semantics of the Postgres collection (`document_listing_sql`): sort fields
and buckets are integer fields (documents without them are left out), ties
keep the first-write order (the position of the page's last key in the
collection; a key that is gone skips the rest of its ties), an exclusion
keeps documents without the field, a missing field is absent or null,
and a group value is the field as
`document ->> field` gives it.
"""

import bisect
from collections.abc import Sequence

from app.adapters.storage.in_memory_document_lookup import (
    JsonObject,
    field_text,
    is_matching,
    is_within,
    parse_object,
)
from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentLatestQuery, DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.storage.constrained_integers import (
    DocumentBucketIndex,
    DocumentCount,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger, DocumentFieldSum
from app.schemas.typings.storage.strings import DocumentFieldText

type GroupKey = tuple[tuple[str | None, ...], int | None]


def select_page(
    entries: Sequence[tuple[str, str]],
    query: DocumentPageQuery,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> list[str]:
    """The serialized documents of one keyset page, in page order."""

    keyed: list[tuple[tuple[int, ...], int, str]] = []
    written_at: dict[str, int] = {}
    for written, (key, serialized) in enumerate(entries):
        written_at[key] = written
        document: JsonObject | None = parse_object(serialized)
        if document is None or not is_in_filter(document, query.where, fields):
            continue

        values: tuple[int, ...] | None = integer_values(document, query.sort_fields)
        if values is not None:
            keyed.append((values, written, serialized))

    keyed.sort(key=lambda row: (row[0], row[1]), reverse=query.is_descending)
    if query.after is not None:
        after_values: tuple[int, ...] = tuple(
            int(value) for value in query.after.values
        )
        after_written: int | None = written_at.get(str(query.after.document_key))
        keyed = [
            row
            for row in keyed
            if is_after(
                row[0], row[1], after_values, after_written, query.is_descending
            )
        ]

    return [serialized for _, _, serialized in keyed[: int(query.limit)]]


def select_latest(
    entries: Sequence[tuple[str, str]],
    query: DocumentLatestQuery,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> list[str]:
    """The newest matching serialized document of each group, in group order."""

    wanted: list[str] = list(dict.fromkeys(str(value) for value in query.groups))
    newest: dict[str, tuple[int, int, str]] = {}
    for written, (_, serialized) in enumerate(entries):
        document: JsonObject | None = parse_object(serialized)
        if document is None or not is_in_filter(document, query.where, fields):
            continue

        group: str | None = field_text(document.get(str(query.group_field)))
        value: int | None = integer_value(document, query.sort_field)
        if group is None or group not in wanted or value is None:
            continue

        if group not in newest or (value, written) > newest[group][:2]:
            newest[group] = (value, written, serialized)

    return [newest[group][2] for group in wanted if group in newest]


def is_after(
    values: tuple[int, ...],
    written: int,
    after_values: tuple[int, ...],
    after_written: int | None,
    is_descending: bool,
) -> bool:
    """Whether a row comes after the position in the page order."""

    if values != after_values:
        return values < after_values if is_descending else values > after_values

    if after_written is None:
        return False

    return written < after_written if is_descending else written > after_written


def aggregate(
    entries: Sequence[tuple[str, str]],
    aggregation: DocumentAggregation,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> list[DocumentGroupCount]:
    """Grouped counts, totals and largest values of the matching documents."""

    counts: dict[GroupKey, int] = {}
    totals: dict[GroupKey, list[int]] = {}
    latest: dict[GroupKey, int] = {}
    for _, serialized in entries:
        document: JsonObject | None = parse_object(serialized)
        if document is None or not is_in_filter(document, aggregation.where, fields):
            continue

        bucket: int | None = None
        if aggregation.buckets is not None:
            value: int | None = integer_value(document, aggregation.buckets.field)
            starts: list[int] = [int(start) for start in aggregation.buckets.starts]
            if value is None or value < starts[0]:
                continue

            bucket = bisect.bisect_right(starts, value) - 1

        group: GroupKey = (
            tuple(
                field_text(document.get(str(field))) for field in aggregation.group_by
            ),
            bucket,
        )
        counts[group] = counts.get(group, 0) + 1
        sums: list[int] = totals.setdefault(group, [0] * len(aggregation.totals_of))
        for index, field in enumerate(aggregation.totals_of):
            sums[index] += integer_value(document, field) or 0

        if aggregation.latest_of is not None:
            moment: int | None = integer_value(document, aggregation.latest_of)
            if moment is not None:
                latest[group] = max(latest.get(group, moment), moment)

    if not counts and not aggregation.group_by and aggregation.buckets is None:
        counts[((), None)] = 0

    return [
        DocumentGroupCount(
            values=tuple(
                None if value is None else DocumentFieldText(value) for value in values
            ),
            bucket=None if bucket is None else DocumentBucketIndex(bucket),
            count=DocumentCount(count),
            totals=tuple(
                DocumentFieldSum(amount)
                for amount in totals.get(
                    (values, bucket), [0] * len(aggregation.totals_of)
                )
            ),
            latest=(
                None
                if (values, bucket) not in latest
                else DocumentFieldInteger(latest[(values, bucket)])
            ),
        )
        for (values, bucket), count in counts.items()
    ]


def is_in_filter(
    document: JsonObject,
    where: DocumentFilter,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> bool:
    if not all(is_matching(document, match, fields) for match in where.matches):
        return False

    if not all(
        any(
            is_matching(
                document, DocumentFieldMatch(field=among.field, value=value), fields
            )
            for value in among.values
        )
        for among in where.among
    ):
        return False

    if any(
        field_text(document.get(str(exclusion.field))) == str(exclusion.value)
        for exclusion in where.excluding
    ):
        return False

    if any(document.get(str(field)) is not None for field in where.missing):
        return False

    return all(is_within(document, within) for within in where.ranges)


def integer_values(
    document: JsonObject,
    sort_fields: Sequence[DocumentFieldPath],
) -> tuple[int, ...] | None:
    values: list[int] = []
    for field in sort_fields:
        value: int | None = integer_value(document, field)
        if value is None:
            return None

        values.append(value)

    return tuple(values)


def integer_value(document: JsonObject, field: DocumentFieldPath) -> int | None:
    value: object = document.get(str(field))
    if isinstance(value, int) and not isinstance(value, bool):
        return value

    return None
