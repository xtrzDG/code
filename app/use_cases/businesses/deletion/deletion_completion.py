"""The last steps of a business's deletion: its brand let go, the ledger completed."""

from typed_time_provider import Microseconds

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessDeletionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.utilities.business_closures.certificate_digest import certificate_digest

BUSINESS_ENTITY: AuditEntityName = AuditEntityName("business")


class DeletionCompletion:
    """
    A location leaves its brand (no manager keeps it assigned; the brand,
    its team and its other locations stay), then the ledger entry is
    completed with the certificate's fingerprint and the platform's own
    audit chain records the deletion with how many rows and files went (the
    business's chain keeps its entries until the audit retention purge:
    an append-only log is never edited).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        brand_repo: BrandRepoContract,
        deletion_repo: BusinessDeletionRepoContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def leave_brand(self, business_id: BusinessId, now: Microseconds) -> None:
        business: BusinessDocument | None = self._business_repo.get(business_id)
        if business is None or business.brand_id is None:
            return

        if self._brand_repo.get(business.brand_id) is None:
            return

        def unassign(brand: BrandDocument) -> None:
            for member in brand.members:
                member.business_ids = [
                    location
                    for location in member.business_ids
                    if location != business_id
                ]
            brand.updated_at = now

        self._brand_repo.update(business.brand_id, unassign)

    def complete(
        self, entry: BusinessDeletionDocument, now: Microseconds
    ) -> BusinessDeletionDocument:
        """
        The platform's audit entry first, then the ledger entry completed: a
        job that dies in between records the deletion again on its retry,
        never not at all.
        """

        if entry.completed_at is not None:
            return entry

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=None,
                actor_id=None,
                action=AuditAction.DELETE,
                entity=BUSINESS_ENTITY,
                entity_id=AuditEntityReference(str(entry.deleted_business_id)),
                record_count=AuditRecordCount(
                    sum(int(item.row_count) for item in entry.erased_rows)
                    + int(entry.erased_files or 0)
                ),
                created_at=now,
                updated_at=now,
            )
        )

        def finish(stored: BusinessDeletionDocument) -> BusinessDeletionDocument | None:
            if stored.completed_at is not None:
                return None

            stored.completed_at = now
            stored.updated_at = now
            stored.certificate_digest = certificate_digest(stored)
            return stored

        completed: BusinessDeletionDocument | None = self._deletion_repo.modify(
            entry.id, finish
        )
        stored: BusinessDeletionDocument | None = (
            completed if completed is not None else self._deletion_repo.get(entry.id)
        )
        if stored is None:
            raise ConflictError(f"The deletion ledger entry {entry.id} disappeared.")

        return stored
