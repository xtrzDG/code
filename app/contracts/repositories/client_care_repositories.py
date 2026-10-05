"""
Persistence contracts of the admin's client care (migration 1143): the
credit ledger, the platform team's notes, health changes and digests.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.client_health import AdminDigestKind, ClientHealthStatus
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.client_health_changes import (
    AdminDigestStateDocument,
    ClientHealthChangeDocument,
)
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class BillingCreditRepoContract(RepoContract, Protocol):
    def record(self, line: BillingCreditDocument) -> bool:
        """
        Store a ledger line unless one with its id exists (atomic, also
        across processes): an invoice uses credit once. True when stored.
        """
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[BillingCreditDocument]:
        """Every line of the business's ledger (a few a month), oldest first."""
        raise NotImplementedError


class ClientNoteRepoContract(RepoContract, Protocol):
    def save(self, note: ClientNoteDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, note_id: ClientNoteId
    ) -> ClientNoteDocument | None:
        raise NotImplementedError

    def delete(self, business_id: BusinessId, note_id: ClientNoteId) -> None:
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[ClientNoteDocument]:
        """The client's notes, at most `limit`, in first-write order."""
        raise NotImplementedError


class ClientHealthChangeRepoContract(RepoContract, Protocol):
    def add(self, change: ClientHealthChangeDocument) -> None:
        raise NotImplementedError

    def list_before(
        self,
        business_id: BusinessId,
        before: Microseconds | None,
        limit: DocumentQueryLimit,
    ) -> list[ClientHealthChangeDocument]:
        """The client's changes before a moment, newest first, at most `limit`."""
        raise NotImplementedError

    def list_changes_to(
        self,
        status: ClientHealthStatus,
        changed_from: Microseconds,
        changed_before: Microseconds,
    ) -> list[ClientHealthChangeDocument]:
        """Changes of any client to `status` in the time range (platform-wide)."""
        raise NotImplementedError


class AdminDigestStateRepoContract(RepoContract, Protocol):
    def get(self, kind: AdminDigestKind) -> AdminDigestStateDocument | None:
        raise NotImplementedError

    def save(self, state: AdminDigestStateDocument) -> None:
        raise NotImplementedError
