import threading
from collections.abc import Callable, Mapping, Sequence

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.in_memory_document_listing import aggregate, select_page
from app.adapters.storage.in_memory_document_lookup import select_entries
from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentPageQuery
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
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.schemas.typings.storage.strings import DocumentFieldText
from app.utilities.storage.document_lookup_fields import (
    catalog_name_of,
    declared_lookup_fields,
    require_valid_lookup,
)
from app.utilities.storage.document_query_rules import (
    require_valid_aggregation,
    require_valid_page,
)
from app.utilities.storage.storage_scoping import require_tenant_scope


class InMemoryDocumentCollectionAdapter[StoredDocument: PersistentDocument](
    DocumentCollectionAdapterContract[StoredDocument]
):
    """
    Thread-safe in-process collection that behaves like a document database.

    Documents are stored as JSON and validated on every read, so callers get
    independent instances and persistence-incompatible fields fail early.
    Writing and reading go through the same `PersistedDocumentCodec` as
    Postgres (current schema version stamped, tolerant upcasting reads).
    Data lives until the process restarts. Queries by field accept the same
    lookup fields as the Postgres collection (by default those the catalog
    declares for the document type), so a query without an index fails in
    in-memory tests too; they scan, which is fine for tests and demos.
    Keyset pages and aggregations follow `in_memory_document_listing`.

    A tenant collection given the process's `tenant_scope` refuses code
    that entered no storage scope, like the Postgres collection
    (`UnscopedStorageAccessError`), so the in-memory app is fail-closed too.
    Rows of other businesses are not filtered here: that is the job of
    repositories and, on Postgres, of row-level security.
    """

    def __init__(
        self,
        document_type: type[StoredDocument],
        lookup_fields: Mapping[DocumentFieldPath, LookupFieldKind] | None = None,
        tenant_scope: StorageScopeContract | None = None,
    ) -> None:
        self._document_type: type[StoredDocument] = document_type
        self._tenant_scope: StorageScopeContract | None = tenant_scope
        self._serialized_documents: dict[str, str] = {}
        self._lock: threading.Lock = threading.Lock()
        collection_name: DocumentCollectionName | None = catalog_name_of(document_type)
        self._codec: PersistedDocumentCodec[StoredDocument] = PersistedDocumentCodec(
            document_type, collection_name
        )
        self._lookup_fields: dict[DocumentFieldPath, LookupFieldKind] = (
            declared_lookup_fields(collection_name, document_type)
            if lookup_fields is None
            else dict(lookup_fields)
        )

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        self._require_scope()
        serialized_document: str = self._codec.encode(document)
        with self._lock:
            self._serialized_documents[document_key] = serialized_document

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

    def page_by(self, query: DocumentPageQuery) -> list[StoredDocument]:
        require_valid_page(self._lookup_fields, query, self._label())
        return self._validate_all(
            select_page(self._entries(), query, self._lookup_fields)
        )

    def count_by(self, aggregation: DocumentAggregation) -> list[DocumentGroupCount]:
        require_valid_aggregation(self._lookup_fields, aggregation, self._label())
        return aggregate(self._entries(), aggregation, self._lookup_fields)

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

    def _entries(self) -> list[tuple[str, str]]:
        """(key, serialized document) in first-write order, after the scope check."""

        self._require_scope()
        with self._lock:
            return list(self._serialized_documents.items())

    def _validate_all(self, serialized_documents: list[str]) -> list[StoredDocument]:
        return [
            self._codec.decode(serialized_document)
            for serialized_document in serialized_documents
        ]

    def _require_scope(self) -> None:
        if self._tenant_scope is not None:
            require_tenant_scope(self._tenant_scope.current(), self._label())

    def _label(self) -> str:
        return f"the {self._document_type.__name__} collection"
