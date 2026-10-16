"""
The in-memory document table: stored JSON, the codec, the scope check and
the keyset pages, latest documents and aggregations of
`in_memory_document_listing` (the collection adds lookups and writes).
"""

import threading
from collections.abc import Mapping

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.in_memory_document_listing import (
    aggregate,
    select_latest,
    select_page,
    select_page_positions,
)
from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import (
    DocumentLatestQuery,
    DocumentPagePosition,
    DocumentPageQuery,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.utilities.storage.document_lookup_fields import (
    catalog_name_of,
    declared_lookup_fields,
)
from app.utilities.storage.document_query_rules import (
    require_valid_aggregation,
    require_valid_latest,
    require_valid_page,
)
from app.utilities.storage.storage_scoping import require_tenant_scope


class InMemoryDocumentTable[StoredDocument: PersistentDocument]:
    """Base of `InMemoryDocumentCollectionAdapter` (see its description)."""

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

    def page_by(self, query: DocumentPageQuery) -> list[StoredDocument]:
        require_valid_page(self._lookup_fields, query, self._label())
        return self._validate_all(
            select_page(self._entries(), query, self._lookup_fields)
        )

    def page_positions_by(self, query: DocumentPageQuery) -> list[DocumentPagePosition]:
        require_valid_page(self._lookup_fields, query, self._label())
        return select_page_positions(self._entries(), query, self._lookup_fields)

    def latest_by(self, query: DocumentLatestQuery) -> list[StoredDocument]:
        require_valid_latest(self._lookup_fields, query, self._label())
        return self._validate_all(
            select_latest(self._entries(), query, self._lookup_fields)
        )

    def count_by(self, aggregation: DocumentAggregation) -> list[DocumentGroupCount]:
        require_valid_aggregation(self._lookup_fields, aggregation, self._label())
        return aggregate(self._entries(), aggregation, self._lookup_fields)

    def _entries(self) -> list[tuple[str, str]]:
        """(key, serialized document) in first-write order, after the scope check."""

        self._require_scope()
        with self._lock:
            return list(self._serialized_documents.items())

    def _validate_all(self, serialized_documents: list[str]) -> list[StoredDocument]:
        return [self._codec.decode(serialized) for serialized in serialized_documents]

    def _require_scope(self) -> None:
        if self._tenant_scope is not None:
            require_tenant_scope(self._tenant_scope.current(), self._label())

    def _label(self) -> str:
        return f"the {self._document_type.__name__} collection"
