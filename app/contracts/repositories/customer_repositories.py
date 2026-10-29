"""
Customers: the team's card on a contact (tags, VIP, block), what customers
did across channels (visits, calls, their latest conversations and
bookings), saved segments and the team's customer settings.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.customers.customer_records import ContactVisits, CustomerPageFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId, CustomerSegmentId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class CustomerCardRepoContract(RepoContract, Protocol):
    """The card fields of contacts, which a plain contact save never changes."""

    def change_card(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
        apply: Callable[[ContactDocument], None],
    ) -> ContactDocument | None:
        """
        Apply a change to the contact as stored now, in one step (a row
        lock on Postgres), so two changes at once both land; None, and
        nothing written, for a missing contact.
        """
        raise NotImplementedError

    def page_customers(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        page_filter: CustomerPageFilter,
    ) -> list[ContactDocument]:
        """
        One keyset page of the customers, the most recently active first
        (`last_seen_at`), narrowed by the filter.
        """
        raise NotImplementedError


class CustomerHistoryRepoContract(RepoContract, Protocol):
    """What customers did, read by customer (indexed), never a whole history."""

    def visits_for_contacts(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
        before: Microseconds,
    ) -> dict[ContactId, ContactVisits]:
        """The visits of each customer before `before`; none: left out."""
        raise NotImplementedError

    def calls_of_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> list[CallDocument]:
        """The calls of these (phone) conversations, the latest first."""
        raise NotImplementedError

    def latest_conversations_of(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        """These customers' conversations, the latest message first (no test chats)."""
        raise NotImplementedError

    def latest_bookings_of(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
        limit: DocumentQueryLimit,
    ) -> list[BookingDocument]:
        """These customers' bookings, the latest start first (no test chats)."""
        raise NotImplementedError


class CustomerSegmentRepoContract(RepoContract, Protocol):
    def save(self, segment: CustomerSegmentDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, segment_id: CustomerSegmentId
    ) -> CustomerSegmentDocument | None:
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[CustomerSegmentDocument]:
        """The business's segments, the oldest first (a few per business)."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, segment_id: CustomerSegmentId) -> None:
        raise NotImplementedError


class CustomerSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> CustomerSettingsDocument | None:
        raise NotImplementedError

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[CustomerSettingsDocument], None],
        now: Microseconds,
    ) -> CustomerSettingsDocument:
        """Create the settings when missing, then apply the change in one step."""
        raise NotImplementedError
