"""The consent ledger (1246): every consent and withdrawal, append-only."""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId


class ConsentRecordRepoContract(
    BusinessDocumentPagesContract[ConsentRecordDocument], RepoContract, Protocol
):
    def append(self, record: ConsentRecordDocument) -> None:
        """Add an entry; an entry is never changed or deleted afterwards."""
        raise NotImplementedError

    def list_by_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> list[ConsentRecordDocument]:
        """The customer's entries, oldest first (also after their erasure)."""
        raise NotImplementedError
