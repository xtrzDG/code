"""
Persistence contracts of the audit log and DPA acceptances.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved.
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.contracts.repositories.conversation_listing_contracts import (
    AuditLogListingContract,
)
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditViewCount
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId


class AuditLogRepoContract(
    AuditLogListingContract,
    BusinessDocumentPagesContract[AuditLogEntryDocument],
    RepoContract,
    Protocol,
):
    def append(self, entry: AuditLogEntryDocument) -> None:
        """
        Store a new entry at the end of its hash chain (its business's, or
        the platform's when it names no business). Stored entries are never
        changed or deleted. A VIEW identical to one stored in the last 5
        minutes (same business, person, entity, record and address) adds
        no entry: it raises the first one's view count (`view_counts`).

        Raises:
            ConflictError: an entry with this id is stored already.
        """
        raise NotImplementedError

    def view_counts(
        self,
        business_id: BusinessId,
        entry_ids: Sequence[AuditLogEntryId],
    ) -> dict[AuditLogEntryId, AuditViewCount]:
        """
        How many identical views each of these VIEW entries stands for, in
        one read; an entry missing from the answer stands for one view.
        """
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AuditLogEntryDocument]:
        raise NotImplementedError


class DpaAcceptanceRepoContract(RepoContract, Protocol):
    def save(self, acceptance: DpaAcceptanceDocument) -> None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[DpaAcceptanceDocument]:
        raise NotImplementedError
