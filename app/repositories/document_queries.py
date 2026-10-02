"""
Building blocks of indexed repository queries: matches, ranges and orders
over the lookup fields of `app/utilities/storage/document_lookup_fields.py`.

A typed value turns into its stored text here (an id or hash as its string,
an enum as its value), the form storage compares.
"""

from collections.abc import Iterable
from enum import StrEnum

from typed_time_provider import Microseconds

from app.schemas.dto.paging import KeysetPosition
from app.schemas.dto.storage_pages import DocumentPagePosition
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldExclusion,
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText, StoredDocumentKey
from app.utilities.storage.document_lookup_fields import BUSINESS_ID_FIELD

IS_SANDBOX_FIELD: DocumentFieldPath = DocumentFieldPath("is_sandbox")
CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")


def stored_text(value: object) -> DocumentFieldText:
    """A typed value as storage compares it: an enum by its value, a flag as
    "true"/"false", anything else as its string."""

    if isinstance(value, StrEnum):
        return DocumentFieldText(value.value)

    if isinstance(value, bool):
        return DocumentFieldText("true" if value else "false")

    return DocumentFieldText(str(value))


def field_equals(field: DocumentFieldPath, value: object) -> DocumentFieldMatch:
    """`field` equal to a typed value (an enum compares by its value)."""

    return DocumentFieldMatch(field=field, value=stored_text(value))


def field_among(
    field: DocumentFieldPath, values: Iterable[object]
) -> DocumentFieldAmong:
    """`field` equal to one of the typed values."""

    return DocumentFieldAmong(
        field=field, values=tuple(stored_text(value) for value in values)
    )


def field_other_than(field: DocumentFieldPath, value: object) -> DocumentFieldExclusion:
    """`field` not equal to the typed value (a missing field passes)."""

    return DocumentFieldExclusion(field=field, value=stored_text(value))


def without_sandbox() -> DocumentFieldExclusion:
    """Leave out the owner's test chat and autotests (`is_sandbox` true)."""

    return field_other_than(IS_SANDBOX_FIELD, True)


def document_position(position: KeysetPosition | None) -> DocumentPagePosition | None:
    """A list position as the storage position of `page_by`."""

    if position is None:
        return None

    return DocumentPagePosition(
        values=tuple(
            DocumentFieldInteger(int(value)) for value in position.sort_values
        ),
        document_key=StoredDocumentKey(str(position.item_key)),
    )


def of_business(business_id: BusinessId) -> DocumentFieldMatch:
    """Documents of one business (the indexed `business_id` column)."""

    return field_equals(BUSINESS_ID_FIELD, business_id)


def time_range(
    field: DocumentFieldPath,
    starting_at: Microseconds | None = None,
    ending_before: Microseconds | None = None,
) -> DocumentFieldRange:
    """A timestamp field from `starting_at` (inclusive) to `ending_before`."""

    return DocumentFieldRange(
        field=field,
        lower=None if starting_at is None else DocumentFieldInteger(int(starting_at)),
        upper=(
            None if ending_before is None else DocumentFieldInteger(int(ending_before))
        ),
    )


def ascending(field: DocumentFieldPath) -> DocumentFieldOrder:
    return DocumentFieldOrder(field=field)


def descending(field: DocumentFieldPath) -> DocumentFieldOrder:
    return DocumentFieldOrder(field=field, is_descending=True)
