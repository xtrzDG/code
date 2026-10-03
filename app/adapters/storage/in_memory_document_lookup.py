"""
Indexed queries evaluated on stored JSON in memory, with the semantics of
the Postgres collection: field values compared as `document ->> field`
gives them, integer ranges with an inclusive lower and an exclusive upper
bound, ties in first-write order in both directions, and documents without
the sort field sorted as if it were larger than every value (Postgres puts
NULL last in ascending and first in descending order).
"""

import json
from collections.abc import Sequence

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentLookup,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.storage.document_lookup_fields import split_element_path

type JsonObject = dict[str, object]


def select_entries(
    entries: Sequence[tuple[str, str]],
    lookup: DocumentLookup,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> list[tuple[str, str]]:
    """
    The (key, serialized document) entries `lookup` returns, in its order
    and limit; `entries` are in first-write order.
    """

    selected: list[tuple[JsonObject, tuple[str, str]]] = []
    for entry in entries:
        document: JsonObject | None = parse_object(entry[1])
        if document is not None and is_selected(document, lookup, fields):
            selected.append((document, entry))

    if lookup.order is not None:
        # A stable sort: ties stay in first-write order, also when reversed.
        order_field: str = str(lookup.order.field)
        selected.sort(
            key=lambda entry: sort_value(entry[0].get(order_field)),
            reverse=lookup.order.is_descending,
        )

    found: list[tuple[str, str]] = [entry[1] for entry in selected]
    if lookup.limit is not None:
        return found[: int(lookup.limit)]

    return found


def is_selected(
    document: JsonObject,
    lookup: DocumentLookup,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> bool:
    if not all(is_matching(document, match, fields) for match in lookup.matches):
        return False

    return lookup.within is None or is_within(document, lookup.within)


def is_matching(
    document: JsonObject,
    match: DocumentFieldMatch,
    fields: dict[DocumentFieldPath, LookupFieldKind],
) -> bool:
    if fields.get(match.field) is LookupFieldKind.ELEMENT_TEXT:
        list_field, element_field = split_element_path(match.field)
        return any(
            field_text(element.get(element_field)) == str(match.value)
            for element in list_objects(document.get(list_field))
        )

    return field_text(document.get(str(match.field))) == str(match.value)


def is_within(document: JsonObject, within: DocumentFieldRange) -> bool:
    value: object = document.get(str(within.field))
    if not isinstance(value, int) or isinstance(value, bool):
        return False

    if within.lower is not None and value < int(within.lower):
        return False

    return within.upper is None or value < int(within.upper)


def sort_value(value: object) -> tuple[int, int]:
    """Integers in order; a missing or non-integer value after all of them."""

    if isinstance(value, int) and not isinstance(value, bool):
        return (0, value)

    return (1, 0)


def parse_object(serialized_document: str) -> JsonObject | None:
    return as_object(json.loads(serialized_document))


def as_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None

    items: list[tuple[object, object]] = list(value.items())  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    return {str(key): item for key, item in items}


def list_objects(value: object) -> list[JsonObject]:
    """The objects of a JSON list (other elements are skipped)."""

    if not isinstance(value, list):
        return []

    elements: list[object] = list(value)  # pyright: ignore[reportUnknownArgumentType]
    return [
        element_object
        for element in elements
        if (element_object := as_object(element)) is not None
    ]


def field_text(value: object) -> str | None:
    """A field value as Postgres `->>` gives it (text), None for null."""

    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value)
