"""An in-memory audit collection that fails any write but an insert."""

from collections.abc import Callable, Sequence

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.storage.booleans import IsDocumentInserted


class AppendOnlyCollection(InMemoryDocumentCollectionAdapter[AuditLogEntryDocument]):
    """Counts inserts; an update, overwrite or deletion fails the test."""

    def __init__(self) -> None:
        super().__init__(AuditLogEntryDocument)
        self.inserted: int = 0

    def insert_if_absent(
        self, document_key: str, document: AuditLogEntryDocument
    ) -> IsDocumentInserted:
        inserted = super().insert_if_absent(document_key, document)
        self.inserted += 1 if inserted else 0
        return inserted

    def upsert(self, document_key: str, document: AuditLogEntryDocument) -> None:
        raise AssertionError(f"An audit entry was overwritten: {document_key}")

    def upsert_many(self, entries: Sequence[tuple[str, AuditLogEntryDocument]]) -> None:
        raise AssertionError("Audit entries were overwritten in bulk.")

    def modify(
        self,
        document_key: str,
        change: Callable[[AuditLogEntryDocument], AuditLogEntryDocument | None],
    ) -> AuditLogEntryDocument | None:
        raise AssertionError(f"An audit entry was changed: {document_key}")

    def delete(self, document_key: str) -> None:
        raise AssertionError(f"An audit entry was deleted: {document_key}")
