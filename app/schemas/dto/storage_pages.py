"""Keyset pages of a document collection (`page_by` of the store contract)."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator

from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.storage.booleans import IsDescendingOrder
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import StoredDocumentKey

MAX_SORT_FIELDS: int = 3


class DocumentPagePosition(ImmutableDTO):
    """
    Where the previous page ended: the sort field values and the storage
    key of its last document (storage finds the key's first write, the tie
    order). The next page starts strictly after it.
    """

    values: tuple[DocumentFieldInteger, ...]
    document_key: StoredDocumentKey


class DocumentPageQuery(ImmutableDTO):
    """
    One keyset page: the documents that meet `where` and have every sort
    field, ordered by the INTEGER sort fields and then their first write
    (ties keep the order they were written in), all ascending or all
    descending, starting after `after`, at most `limit` of them. The cost of
    a page does not grow with how many pages came before it.
    """

    where: DocumentFilter = Field(default_factory=DocumentFilter)
    sort_fields: tuple[DocumentFieldPath, ...]
    is_descending: IsDescendingOrder = True
    after: DocumentPagePosition | None = None
    limit: DocumentQueryLimit

    @model_validator(mode="after")
    def require_matching_position(self) -> Self:
        if not 1 <= len(self.sort_fields) <= MAX_SORT_FIELDS:
            raise ValueError(f"A page sorts by 1 to {MAX_SORT_FIELDS} fields.")

        if self.after is not None and len(self.after.values) != len(self.sort_fields):
            raise ValueError("A page position needs one value per sort field.")

        return self
