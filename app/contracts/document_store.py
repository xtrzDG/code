"""Storage-neutral document collection contract used by repositories."""

from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar

from base_pydantic_schemas import PersistentDocument

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentLatestQuery, DocumentPageQuery
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
)
from app.schemas.typings.storage.booleans import IsDescendingOrder, IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText

StoredDocument = TypeVar("StoredDocument", bound=PersistentDocument)


class DocumentCollectionAdapterContract(AdapterContract, Protocol[StoredDocument]):
    """
    One named collection of documents of a single type.

    Keys are technical storage keys (usually the document id as str).
    Implementations serialize on write and validate on read, so callers always
    receive fresh, independent instances.

    Queries by field go through lookup fields that the collection declares
    (`app/utilities/storage/document_lookup_fields.py`) and the migrations
    index; an undeclared field, or a field of the wrong kind, raises
    `UndeclaredLookupFieldError` on every storage, so a missing index shows
    up in in-memory tests already. `list_all` reads the whole collection and
    is meant for admin views, exports and jobs that walk every business.
    """

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        raise NotImplementedError

    def upsert_many(self, entries: Sequence[tuple[str, StoredDocument]]) -> None:
        """Write many (key, document) pairs in one transaction: bulk loads
        (`workshop seed-load`), never a request's own writes."""
        raise NotImplementedError

    def get(self, document_key: str) -> StoredDocument | None:
        raise NotImplementedError

    def list_all(self) -> list[StoredDocument]:
        raise NotImplementedError

    def get_many(self, document_keys: Sequence[str]) -> list[StoredDocument]:
        """The stored documents of these keys (missing ones skipped), in no
        particular order: one indexed read for a page's related documents."""
        raise NotImplementedError

    def find_one_by_field(
        self,
        field: DocumentFieldPath,
        value: DocumentFieldText,
    ) -> StoredDocument | None:
        """
        The first-written document whose TEXT or ELEMENT_TEXT lookup field
        has this value (an indexed lookup), or None.
        """
        raise NotImplementedError

    def list_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        """
        Documents matching every field (indexed), in first-write order or
        sorted by an INTEGER lookup field, at most `limit` of them.
        """
        raise NotImplementedError

    def count_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        within: DocumentFieldRange | None = None,
    ) -> DocumentCount:
        """How many documents match every field and lie within the range."""
        raise NotImplementedError

    def list_by_range(
        self,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
        is_descending: IsDescendingOrder = False,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        """
        Documents whose INTEGER lookup field lies within the range (and that
        match every field), sorted by that field, at most `limit` of them.
        """
        raise NotImplementedError

    def page_by(self, query: DocumentPageQuery) -> list[StoredDocument]:
        """
        One keyset page (`DocumentPageQuery`): on Postgres an index range
        scan that starts at the position, so page 1000 costs what page 1
        costs.
        """
        raise NotImplementedError

    def latest_by(self, query: DocumentLatestQuery) -> list[StoredDocument]:
        """The newest matching document of each group (one indexed probe per
        group): a page's latest messages, never the whole conversations."""
        raise NotImplementedError

    def count_by(self, aggregation: DocumentAggregation) -> list[DocumentGroupCount]:
        """
        Grouped counts, sums and maxima (`DocumentAggregation`) computed by
        the database: no document is read into the application.
        """
        raise NotImplementedError

    def delete_by_range(
        self,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
    ) -> DocumentCount:
        """
        Delete the documents `list_by_range` would return (in small batches
        on Postgres, so no long lock is held); returns how many.
        """
        raise NotImplementedError

    def insert_if_absent(
        self,
        document_key: str,
        document: StoredDocument,
    ) -> IsDocumentInserted:
        """
        Store a new document in one atomic step: False, and nothing
        written, when the key (or a unique index of the collection) is
        already taken, even by a concurrent writer in another process.
        """
        raise NotImplementedError

    def modify(
        self,
        document_key: str,
        change: Callable[[StoredDocument], StoredDocument | None],
    ) -> StoredDocument | None:
        """
        Read the stored document, let `change` turn it into the document to
        store, and write that, in one step (no other write of this document
        can come in between: a row lock on Postgres, the collection lock in
        memory). Returns what was written; None, and nothing written, when
        the document is missing or `change` returns None. An error raised by
        `change` leaves the document as it was. `change` must not use this
        collection itself.
        """
        raise NotImplementedError

    def replace_if(
        self,
        document_key: str,
        document: StoredDocument,
        is_current: Callable[[StoredDocument], bool],
    ) -> bool:
        """
        Overwrite the stored document only when `is_current` accepts it, in
        one step (no other write can come in between: a row lock on
        Postgres, the collection lock in memory). False, and nothing
        written, when the document is missing or not accepted. Used for
        optimistic concurrency (compare a revision).
        """
        raise NotImplementedError

    def delete(self, document_key: str) -> None:
        raise NotImplementedError
