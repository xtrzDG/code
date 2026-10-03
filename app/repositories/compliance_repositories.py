from app.contracts.repositories.compliance_repositories import (
    AuditLogRepoContract,
    DpaAcceptanceRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import of_business
from app.repositories.listing.audit_listing import AuditLogListing
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AuditLogRepository(AuditLogListing, AuditLogRepoContract):
    """Append-only audit log; entries without a business are platform-wide."""

    def append(self, entry: AuditLogEntryDocument) -> None:
        if self._collection.get(str(entry.id)) is not None:
            raise ConflictError(f"Audit entry {entry.id} is already stored.")

        self._collection.upsert(str(entry.id), entry)

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AuditLogEntryDocument]:
        return sorted(
            self._collection.list_by_fields([of_business(business_id)]),
            key=lambda entry: entry.created_at,
        )


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
            self._list_in_business(business_id),
            key=lambda acceptance: acceptance.accepted_at,
        )
