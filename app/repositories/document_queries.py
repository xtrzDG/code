"""
Building blocks of indexed repository queries: matches, ranges and orders
over the lookup fields of `app/utilities/storage/document_lookup_fields.py`.

A typed value turns into its stored text here (an id or hash as its string,
an enum as its value), the form storage compares.
"""

from enum import StrEnum

from typed_time_provider import Microseconds

from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_lookup_fields import BUSINESS_ID_FIELD


def field_equals(field: DocumentFieldPath, value: object) -> DocumentFieldMatch:
    """`field` equal to a typed value (an enum compares by its value)."""

    stored_text: str = value.value if isinstance(value, StrEnum) else str(value)
    return DocumentFieldMatch(field=field, value=DocumentFieldText(stored_text))


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
