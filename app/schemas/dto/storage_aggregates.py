"""Grouped counts of a document collection (`count_by` of the store contract)."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator

from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.storage.constrained_integers import (
    DocumentBucketIndex,
    DocumentCount,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger, DocumentFieldSum
from app.schemas.typings.storage.strings import DocumentFieldText


class DocumentFieldBuckets(ImmutableDTO):
    """
    Buckets of an INTEGER lookup field (local days, opening hours): bucket
    i holds the values from `starts[i]` up to the next start, the last one
    every larger value. Documents below the first start, or without the
    field, are left out of the aggregation.
    """

    field: DocumentFieldPath
    starts: tuple[DocumentFieldInteger, ...]

    @model_validator(mode="after")
    def require_ascending_starts(self) -> Self:
        if not self.starts:
            raise ValueError("Buckets need at least one start.")

        if any(
            int(later) <= int(earlier)
            for earlier, later in zip(self.starts, self.starts[1:], strict=False)
        ):
            raise ValueError("Bucket starts must strictly ascend.")

        return self


class DocumentAggregation(ImmutableDTO):
    """
    Count the documents that meet `where`, per combination of the values
    of the `group_by` fields (TEXT or FILTER_TEXT lookup fields) and per
    bucket. Optionally each group also sums INTEGER fields (`totals_of`)
    and takes the largest value of one (`latest_of`).

    Without groups or buckets the answer is exactly one group (count 0 when
    nothing matches); with them, only groups that have documents.
    """

    where: DocumentFilter = Field(default_factory=DocumentFilter)
    group_by: tuple[DocumentFieldPath, ...] = Field(
        default_factory=tuple[DocumentFieldPath, ...]
    )
    buckets: DocumentFieldBuckets | None = None
    totals_of: tuple[DocumentFieldPath, ...] = Field(
        default_factory=tuple[DocumentFieldPath, ...]
    )
    latest_of: DocumentFieldPath | None = None


class DocumentGroupCount(ImmutableDTO):
    """
    One group of an aggregation: the `group_by` values in their order (None
    for a missing field), the bucket, how many documents, the asked totals
    in their order (0 when no document has the field) and largest value
    (None when not asked or no document has the field).
    """

    values: tuple[DocumentFieldText | None, ...] = Field(
        default_factory=tuple[DocumentFieldText | None, ...]
    )
    bucket: DocumentBucketIndex | None = None
    count: DocumentCount
    totals: tuple[DocumentFieldSum, ...] = Field(
        default_factory=tuple[DocumentFieldSum, ...]
    )
    latest: DocumentFieldInteger | None = None
