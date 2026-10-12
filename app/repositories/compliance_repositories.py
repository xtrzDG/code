from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.repositories.compliance_repositories import (
    AuditLogRepoContract,
    DpaAcceptanceRepoContract,
)
from app.repositories.audit.audit_chain_appending import AuditChainAppending
from app.repositories.audit.audit_view_counting import AuditViewCounting
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import of_business
from app.repositories.listing.audit_listing import AuditLogListing
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
    AuditViewCountDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditViewCount
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId


class AuditLogRepository(AuditLogListing, AuditLogRepoContract):
    """
    The append-only, hash-chained audit log: every entry joins its
    business's chain, or the platform's when it names no business
    (`AuditChainAppending`); a repeated identical view raises the first
    one's count beside the chain (`AuditViewCounting`). No stored entry is
    ever changed or deleted here (the database refuses it too, 1193).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[AuditLogEntryDocument],
        view_counts: DocumentCollectionAdapterContract[AuditViewCountDocument],
        checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
        heads: DocumentCollectionAdapterContract[AuditChainHeadDocument],
        advisory_locks: AdvisoryLockAdapterContract,
    ) -> None:
        super().__init__(collection)
        self._views: AuditViewCounting = AuditViewCounting(collection, view_counts)
        self._chain: AuditChainAppending = AuditChainAppending(
            collection, checkpoints, heads, advisory_locks
        )

    def append(self, entry: AuditLogEntryDocument) -> None:
        if self._views.count_if_repeated(entry):
            return

        self._chain.append(entry)

    def view_counts(
        self,
        business_id: BusinessId,
        entry_ids: Sequence[AuditLogEntryId],
    ) -> dict[AuditLogEntryId, AuditViewCount]:
        return self._views.counts_of(business_id, entry_ids)

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
