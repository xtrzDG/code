from collections.abc import Sequence

from base_pydantic_schemas import PersistentDocument

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.repositories.document_queries import of_business
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.booleans import IsDescendingOrder
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)


class BusinessScopedRepository[StoredDocument: PersistentDocument]:
    """
    Base for repositories of tenant-owned documents.

    Reads always check the business id, so a document id taken from another
    tenant returns nothing (the concept's "row level security" rule). Lists
    are indexed queries filtered by the business (`business_id` column)
    first, never a read of the whole collection.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[StoredDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[StoredDocument] = collection

    def _store(self, document_id: str, document: StoredDocument) -> None:
        self._collection.upsert(document_id, document)

    def _load(
        self,
        business_id: BusinessId,
        document_id: str,
    ) -> StoredDocument | None:
        document: StoredDocument | None = self._collection.get(document_id)
        if document is None or read_business_id(document) != business_id:
            return None

        return document

    def _list_in_business(
        self,
        business_id: BusinessId,
        matches: Sequence[DocumentFieldMatch] = (),
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[StoredDocument]:
        """The business's documents matching every field (indexed)."""

        return self._collection.list_by_fields(
            (of_business(business_id), *matches), order=order, limit=limit
        )

    def _find_in_business(
        self,
        business_id: BusinessId,
        matches: Sequence[DocumentFieldMatch],
    ) -> StoredDocument | None:
        """The business's first-written document matching every field."""

        found: list[StoredDocument] = self._list_in_business(
            business_id, matches, limit=DocumentQueryLimit(1)
        )
        return found[0] if found else None

    def _list_in_range(
        self,
        business_id: BusinessId,
        within: DocumentFieldRange,
        matches: Sequence[DocumentFieldMatch] = (),
        is_descending: IsDescendingOrder = False,
    ) -> list[StoredDocument]:
        """The business's documents within a range, sorted by its field."""

        return self._collection.list_by_range(
            within,
            (of_business(business_id), *matches),
            is_descending=is_descending,
        )

    def _count_in_business(
        self,
        business_id: BusinessId,
        matches: Sequence[DocumentFieldMatch],
        within: DocumentFieldRange | None = None,
    ) -> DocumentCount:
        return self._collection.count_by_fields(
            (of_business(business_id), *matches), within
        )

    def _remove(self, business_id: BusinessId, document_id: str) -> None:
        if self._load(business_id, document_id) is not None:
            self._collection.delete(document_id)


def read_business_id(document: PersistentDocument) -> BusinessId | None:
    business_id: object = getattr(document, "business_id", None)
    if isinstance(business_id, BusinessId):
        return business_id

    return None
