from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import (
    AuditLogRepoContract,
    DpaAcceptanceRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AuditLogRepository(AuditLogRepoContract):
    """Append-only audit log; entries without a business are platform-wide."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[AuditLogEntryDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            collection
        )

    def append(self, entry: AuditLogEntryDocument) -> None:
        if self._collection.get(str(entry.id)) is not None:
            raise ConflictError(f"Audit entry {entry.id} is already stored.")

        self._collection.upsert(str(entry.id), entry)

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AuditLogEntryDocument]:
        entries: list[AuditLogEntryDocument] = [
            entry
            for entry in self._collection.list_all()
            if entry.business_id == business_id
        ]
        return sorted(entries, key=lambda entry: entry.created_at)


class DpaAcceptanceRepository(
    BusinessScopedRepository[DpaAcceptanceDocument],
    DpaAcceptanceRepoContract,
):
    def save(self, acceptance: DpaAcceptanceDocument) -> None:
        self._store(str(acceptance.id), acceptance)

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[DpaAcceptanceDocument]:
        return sorted(
            self._list(business_id),
            key=lambda acceptance: acceptance.accepted_at,
        )
