"""Indexed queries of a document collection (`DocumentCollectionAdapterContract`)."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.typings.storage.booleans import IsDescendingOrder
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText


class DocumentFieldMatch(ImmutableDTO):
    """A TEXT or ELEMENT_TEXT lookup field equal to a value."""

    field: DocumentFieldPath
    value: DocumentFieldText


class DocumentFieldAmong(ImmutableDTO):
    """
    A TEXT, FILTER_TEXT or ELEMENT_TEXT lookup field equal to one of the
    values (none: nothing matches).
    """

    field: DocumentFieldPath
    values: tuple[DocumentFieldText, ...]


class DocumentFieldExclusion(ImmutableDTO):
    """
    A TEXT or FILTER_TEXT lookup field other than the value; a document
    without the field is kept (a flag stored before it existed).
    """

    field: DocumentFieldPath
    value: DocumentFieldText


class DocumentFieldRange(ImmutableDTO):
    """
    An INTEGER lookup field from `lower` (inclusive) to `upper` (exclusive);
    a missing bound is open. Documents without the field never match.
    """

    field: DocumentFieldPath
    lower: DocumentFieldInteger | None = None
    upper: DocumentFieldInteger | None = None

    @model_validator(mode="after")
    def require_a_bound(self) -> Self:
        if self.lower is None and self.upper is None:
            raise ValueError("A field range needs a lower or an upper bound.")

        return self


class DocumentFieldOrder(ImmutableDTO):
    """
    Sort by an INTEGER lookup field, ascending or descending; ties keep the
    first-write order in both directions (like Python's stable sort).
    """

    field: DocumentFieldPath
    is_descending: IsDescendingOrder = False


class DocumentLookup(ImmutableDTO):
    """
    One indexed query: every match and the range must hold. Without an
    order, documents come in first-write order.
    """

    matches: tuple[DocumentFieldMatch, ...] = Field(
        default_factory=tuple[DocumentFieldMatch, ...]
    )
    within: DocumentFieldRange | None = None
    order: DocumentFieldOrder | None = None
    limit: DocumentQueryLimit | None = None


class DocumentFilter(ImmutableDTO):
    """
    The conditions of a page or an aggregation: every match, among, and
    exclusion and every range must hold.
    """

    matches: tuple[DocumentFieldMatch, ...] = Field(
        default_factory=tuple[DocumentFieldMatch, ...]
    )
    among: tuple[DocumentFieldAmong, ...] = Field(
        default_factory=tuple[DocumentFieldAmong, ...]
    )
    excluding: tuple[DocumentFieldExclusion, ...] = Field(
        default_factory=tuple[DocumentFieldExclusion, ...]
    )
    ranges: tuple[DocumentFieldRange, ...] = Field(
        default_factory=tuple[DocumentFieldRange, ...]
    )


class DocumentLookupField(ImmutableDTO):
    """A field a collection may be queried by, and how it is indexed."""

    path: DocumentFieldPath
    kind: LookupFieldKind
