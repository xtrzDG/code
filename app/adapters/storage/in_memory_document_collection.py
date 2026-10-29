from collections.abc import Callable, Sequence

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.in_memory_document_lookup import select_entries
from app.adapters.storage.in_memory_document_table import InMemoryDocumentTable
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
    DocumentLookup,
)
from app.schemas.typings.storage.booleans import IsDescendingOrder, IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_lookup_fields import require_valid_lookup


class InMemoryDocumentCollectionAdapter[StoredDocument: PersistentDocument](
    InMemoryDocumentTable[StoredDocument],
    DocumentCollectionAdapterContract[StoredDocument],
):
    """
    Thread-safe in-process collection that behaves like a document database.

    Documents are stored as JSON (until the process restarts) through the
    `PersistedDocumentCodec` Postgres uses, and validated on every read, so
    callers get independent instances. Queries accept the lookup fields of
    the Postgres collection (by default the catalog's), so a query without
    an index fails in in-memory tests too; they scan, which suits tests
    and demos. Pages, latest documents and aggregations follow
    `in_memory_document_listing`.

    A tenant collection given the process's `tenant_scope` refuses code
    that entered no storage scope, like the Postgres collection
    (`UnscopedStorageAccessError`), so the in-memory app is fail-closed too.
    Rows of other businesses are not filtered here: that is the job of
    repositories and, on Postgres, of row-level security.
    """

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        self._require_scope()
        serialized_document: str = self._codec.encode(document)
        with self._lock:
            self._serialized_documents[document_key] = serialized_document

    def upsert_many(self, entries: Sequence[tuple[str, StoredDocument]]) -> None:
        for document_key, document in entries:
            self.upsert(document_key, document)

    def insert_if_absent(
        self,
        document_key: str,
        document: StoredDocument,
    ) -> IsDocumentInserted:
        self._require_scope()
        serialized_document: str = self._codec.encode(document)
        with self._lock:
            if document_key in self._serialized_documents:
                return False

            self._serialized_documents[document_key] = serialized_document
            return True

    def get(self, document_key: str) -> StoredDocument | None:
        self._require_scope()
        with self._lock:
            serialized_document: str | None = self._serialized_documents.get(
                document_key
            )

        if serialized_document is None:
            return None

        return self._codec.decode(serialized_document)

    def list_all(self) -> list[StoredDocument]:
        self._require_scope()
        with self._lock:
            serialized_documents: list[str] = list(self._serialized_documents.values())

        return self._validate_all(serialized_documents)

    def get_many(self, document_keys: Sequence[str]) -> list[StoredDocument]:
        self._require_scope()
        with self._lock:
            serialized_documents: list[str] = [
                serialized
                for key in dict.fromkeys(document_keys)
                if (serialized := self._serialized_documents.get(key)) is not None
            ]

        return self._validate_all(serialized_documents)

    def find_one_by_field(
        self,
        field: DocumentFieldPath,
        value: DocumentFieldText,
    ) -> StoredDocument | None:
        found: list[StoredDocument] = self._select(
            DocumentLookup(
                matches=(DocumentFieldMatch(field=field, value=value),),
                limit=DocumentQueryLimit(1),
            )
        )
        return found[0] if found else None

    def list_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        return self._select(
            DocumentLookup(matches=tuple(matches), order=order, limit=limit)
        )

    def count_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        within: DocumentFieldRange | None = None,
    ) -> DocumentCount:
        lookup = DocumentLookup(matches=tuple(matches), within=within)
        return DocumentCount(len(self._select_serialized(lookup)))

    def list_by_range(
        self,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
        is_descending: IsDescendingOrder = False,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        return self._select(
            DocumentLookup(
                matches=tuple(matches),
                within=within,
                order=DocumentFieldOrder(
                    field=within.field, is_descending=is_descending
                ),
                limit=limit,
            )
        )

    def delete_by_range(
        self,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
    ) -> DocumentCount:
        lookup = DocumentLookup(matches=tuple(matches), within=within)
        require_valid_lookup(self._lookup_fields, lookup, self._label())
        self._require_scope()
        with self._lock:
            deleted_keys: list[str] = [
                key
                for key, _ in select_entries(
                    list(self._serialized_documents.items()),
                    lookup,
                    self._lookup_fields,
                )
            ]
            for key in deleted_keys:
                del self._serialized_documents[key]

        return DocumentCount(len(deleted_keys))

    def modify(
        self,
        document_key: str,
        change: Callable[[StoredDocument], StoredDocument | None],
    ) -> StoredDocument | None:
        # The whole read-change-write holds the collection lock, so `change`
        # must not call back into this collection (the lock is not
        # reentrant).
        self._require_scope()
        with self._lock:
            stored: str | None = self._serialized_documents.get(document_key)
            if stored is None:
                return None

            changed: StoredDocument | None = change(self._codec.decode(stored))
            if changed is None:
                return None

            serialized_document: str = self._codec.encode(changed)
            self._serialized_documents[document_key] = serialized_document

        return self._codec.decode(serialized_document)

    def replace_if(
        self,
        document_key: str,
        document: StoredDocument,
        is_current: Callable[[StoredDocument], bool],
    ) -> bool:
        return (
            self.modify(
                document_key,
                lambda stored: document if is_current(stored) else None,
            )
            is not None
        )

    def delete(self, document_key: str) -> None:
        self._require_scope()
        with self._lock:
            self._serialized_documents.pop(document_key, None)

    def _select(self, lookup: DocumentLookup) -> list[StoredDocument]:
        return self._validate_all(self._select_serialized(lookup))

    def _select_serialized(self, lookup: DocumentLookup) -> list[str]:
        require_valid_lookup(self._lookup_fields, lookup, self._label())
        return [
            serialized_document
            for _, serialized_document in select_entries(
                self._entries(), lookup, self._lookup_fields
            )
        ]
