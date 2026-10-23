from typing import Protocol

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


class BusinessDocumentTable(Protocol):
    """What a business's deletion needs of an in-memory collection."""

    def count_business_documents(self, business_id: BusinessId) -> DocumentCount: ...

    def remove_business_documents(self, business_id: BusinessId) -> DocumentCount: ...


class InMemoryCollectionRegistry:
    """
    The in-memory collections of one process by name, filled as the storage
    factory builds them (`build_document_collection`): what a business's
    deletion walks when there is no database, where Postgres walks its
    tables. Registering happens while the container wires itself, before
    any request, so the list needs no lock of its own.
    """

    def __init__(self) -> None:
        self._tables: list[tuple[DocumentCollectionName, BusinessDocumentTable]] = []

    def register(
        self, name: DocumentCollectionName, table: BusinessDocumentTable
    ) -> None:
        if all(registered is not table for _, registered in self._tables):
            self._tables.append((name, table))

    def tables(self) -> list[tuple[DocumentCollectionName, BusinessDocumentTable]]:
        return list(self._tables)
