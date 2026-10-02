"""
Persistence contracts of the audit log and DPA acceptances.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved.
"""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.contracts.repositories.conversation_listing_contracts import (
    AuditLogListingContract,
)
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AuditLogRepoContract(AuditLogListingContract, RepoContract, Protocol):
    def append(self, entry: AuditLogEntryDocument) -> None:
        """Audit entries are never updated or deleted."""
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
