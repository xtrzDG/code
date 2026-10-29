"""What a customer did, read for the customer list and one customer's page."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.dto.contacts import ContactActivity, ContactActivityTotals
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId


class ContactActivityRepoContract(RepoContract, Protocol):
    """
    Conversations, bookings and leads by their customer (indexed by
    `contact_id`), the owner's test chats and autotests left out.
    """

    def count_for_contacts(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
    ) -> dict[ContactId, ContactActivityTotals]:
        """
        The totals of each of these customers, counted by the database (no
        record is read); a customer without records is left out.
        """
        raise NotImplementedError

    def list_for_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> ContactActivity:
        """One customer's conversations, bookings and leads."""
        raise NotImplementedError
