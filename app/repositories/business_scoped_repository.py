from base_pydantic_schemas import PersistentDocument

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BusinessScopedRepository[StoredDocument: PersistentDocument]:
    """
    Base for repositories of tenant-owned documents.

    Reads always check the business id, so a document id taken from another
    tenant returns nothing (the concept's "row level security" rule).
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

    def _list(self, business_id: BusinessId) -> list[StoredDocument]:
        return [
            document
            for document in self._collection.list_all()
            if read_business_id(document) == business_id
        ]

    def _list_by_field(
        self,
        business_id: BusinessId,
        field_name: str,
        value: str,
    ) -> list[StoredDocument]:
        """The business's documents whose field has this value (indexed)."""

        return [
            document
            for document in self._collection.list_by_field(field_name, value)
            if read_business_id(document) == business_id
        ]

    def _remove(self, business_id: BusinessId, document_id: str) -> None:
        if self._load(business_id, document_id) is not None:
            self._collection.delete(document_id)


def read_business_id(document: PersistentDocument) -> BusinessId | None:
    business_id: object = getattr(document, "business_id", None)
    if isinstance(business_id, BusinessId):
        return business_id

    return None
