"""Storage-neutral document collection contract used by repositories."""

from typing import Protocol, TypeVar

from base_pydantic_schemas import PersistentDocument

from app.contracts.adapter_contract import AdapterContract

StoredDocument = TypeVar("StoredDocument", bound=PersistentDocument)


class DocumentCollectionAdapterContract(AdapterContract, Protocol[StoredDocument]):
    """
    One named collection of documents of a single type.

    Keys are technical storage keys (usually the document id as str).
    Implementations serialize on write and validate on read, so callers always
    receive fresh, independent instances.
    """

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        raise NotImplementedError

    def get(self, document_key: str) -> StoredDocument | None:
        raise NotImplementedError

    def list_all(self) -> list[StoredDocument]:
        raise NotImplementedError

    def delete(self, document_key: str) -> None:
        raise NotImplementedError
