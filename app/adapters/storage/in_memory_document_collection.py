import json
import threading
from collections.abc import Callable

from base_pydantic_schemas import PersistentDocument

from app.contracts.document_store import DocumentCollectionAdapterContract


class InMemoryDocumentCollectionAdapter[StoredDocument: PersistentDocument](
    DocumentCollectionAdapterContract[StoredDocument]
):
    """
    Thread-safe in-process collection that behaves like a document database.

    Documents are stored as JSON and validated on every read, so callers get
    independent instances and persistence-incompatible fields fail early.
    Data lives until the process restarts.
    """

    def __init__(self, document_type: type[StoredDocument]) -> None:
        self._document_type: type[StoredDocument] = document_type
        self._serialized_documents: dict[str, str] = {}
        self._lock: threading.Lock = threading.Lock()

    def upsert(self, document_key: str, document: StoredDocument) -> None:
        serialized_document: str = document.model_dump_json()
        with self._lock:
            self._serialized_documents[document_key] = serialized_document

    def get(self, document_key: str) -> StoredDocument | None:
        with self._lock:
            serialized_document: str | None = self._serialized_documents.get(
                document_key
            )

        if serialized_document is None:
            return None

        return self._document_type.model_validate_json(serialized_document)

    def list_all(self) -> list[StoredDocument]:
        with self._lock:
            serialized_documents: list[str] = list(self._serialized_documents.values())

        return [
            self._document_type.model_validate_json(serialized_document)
            for serialized_document in serialized_documents
        ]

    def list_by_field(self, field_name: str, value: str) -> list[StoredDocument]:
        with self._lock:
            serialized_documents: list[str] = list(self._serialized_documents.values())

        return [
            self._document_type.model_validate_json(serialized_document)
            for serialized_document in serialized_documents
            if read_field_text(serialized_document, field_name) == value
        ]

    def modify(
        self,
        document_key: str,
        change: Callable[[StoredDocument], StoredDocument | None],
    ) -> StoredDocument | None:
        # The whole read-change-write holds the collection lock, so `change`
        # must not call back into this collection (the lock is not
        # reentrant).
        with self._lock:
            stored: str | None = self._serialized_documents.get(document_key)
            if stored is None:
                return None

            changed: StoredDocument | None = change(
                self._document_type.model_validate_json(stored)
            )
            if changed is None:
                return None

            serialized_document: str = changed.model_dump_json()
            self._serialized_documents[document_key] = serialized_document

        return self._document_type.model_validate_json(serialized_document)

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
        with self._lock:
            self._serialized_documents.pop(document_key, None)


def read_field_text(serialized_document: str, field_name: str) -> str | None:
    """A top-level field as Postgres `document ->> field` gives it (text)."""

    document: object = json.loads(serialized_document)
    if not isinstance(document, dict):
        return None

    field_value: object = document.get(field_name)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if field_value is None:
        return None

    if isinstance(field_value, str):
        return field_value

    return json.dumps(field_value)
