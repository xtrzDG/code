"""
`workshop backfill-lookup`: filling trigger-kept lookup columns of the rows
written before their migration (migrations/README.md, the online-safe
pattern).
"""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator

from app.schemas.typings.storage.booleans import IsLookupBackfillDryRun
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    LookupBackfillBatchCount,
    LookupBackfillBatchSize,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.schemas.typings.storage.strings import StoredDocumentKey

DEFAULT_LOOKUP_BACKFILL_BATCH_SIZE: LookupBackfillBatchSize = LookupBackfillBatchSize(
    5_000
)


class BackfillLookupColumnsCommand(ImmutableDTO):
    """
    Fill one trigger-kept lookup column (`collection_name` and `field`), or
    every one of them when neither is given, `batch_size` rows per
    transaction; a dry run only counts the rows still to fill.
    """

    collection_name: DocumentCollectionName | None = None
    field: DocumentFieldPath | None = None
    batch_size: LookupBackfillBatchSize = DEFAULT_LOOKUP_BACKFILL_BATCH_SIZE
    is_dry_run: IsLookupBackfillDryRun = False

    @model_validator(mode="after")
    def require_collection_with_field(self) -> Self:
        if self.field is not None and self.collection_name is None:
            raise ValueError("A field is named together with its collection.")

        return self


class TriggerLookupColumn(ImmutableDTO):
    """A plain `doc_<field>` column that a trigger fills from `field`."""

    collection_name: DocumentCollectionName
    field: DocumentFieldPath


class LookupBackfillBatch(ImmutableDTO):
    """
    One keyset batch: how many rows it looked at, how many of them it
    filled, and the key of its last row (None when there were no rows
    left after the position it started at).
    """

    last_document_key: StoredDocumentKey | None
    scanned_count: DocumentCount
    filled_count: DocumentCount


class LookupColumnBackfillReport(ImmutableDTO):
    """
    One column: rows looked at and filled in `batch_count` batches; in a
    dry run, `missing` rows still to fill (and nothing scanned or filled).
    """

    collection_name: DocumentCollectionName
    field: DocumentFieldPath
    scanned: DocumentCount = DocumentCount(0)
    filled: DocumentCount = DocumentCount(0)
    missing: DocumentCount = DocumentCount(0)
    batch_count: LookupBackfillBatchCount = LookupBackfillBatchCount(0)


class LookupBackfillReport(ImmutableDTO):
    is_dry_run: IsLookupBackfillDryRun = False
    columns: list[LookupColumnBackfillReport] = Field(
        default_factory=list[LookupColumnBackfillReport]
    )
