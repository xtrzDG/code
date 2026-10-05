"""
Writes and pages of contacts that respect the team's card (tags, VIP,
block): a plain save keeps the card as stored, a card change is one
atomic step, and the customer list pages by last activity with the
card's filters (1140).
"""

from collections.abc import Callable

from app.contracts.repositories.customer_repositories import CustomerCardRepoContract
from app.repositories.document_queries import field_equals
from app.repositories.listing.contact_listing import (
    LAST_SEEN_AT_FIELD,
    ContactListing,
    with_folded_name,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.customers.customer_records import CustomerPageFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.customers.customer_card import keep_card_fields, tag_key

TAG_FIELD: DocumentFieldPath = DocumentFieldPath("tags[].key")
IS_VIP_FIELD: DocumentFieldPath = DocumentFieldPath("is_vip")
IS_BLOCKED_FIELD: DocumentFieldPath = DocumentFieldPath("is_blocked")


class CustomerCardWrites(ContactListing, CustomerCardRepoContract):
    """
    The card-aware writes and the filtered pages of `ContactRepository`
    (`save` keeps the card through `_save_keeping_card`).
    """

    def _save_keeping_card(self, contact: ContactDocument) -> None:
        """
        Overwrite the stored contact except its card, in one step (a row
        lock on Postgres); a new contact is inserted as given. A concurrent
        first save of the same contact makes the insert lose, and the write
        then merges into what it stored.
        """

        key: str = str(contact.id)
        incoming: ContactDocument = with_folded_name(contact)

        def merge(stored: ContactDocument) -> ContactDocument:
            return keep_card_fields(incoming, stored)

        if self._modify_in_business(contact.business_id, key, merge) is not None:
            return

        if self._collection.insert_if_absent(key, incoming):
            return

        self._modify_in_business(contact.business_id, key, merge)

    def change_card(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
        apply: Callable[[ContactDocument], None],
    ) -> ContactDocument | None:
        def change(stored: ContactDocument) -> ContactDocument:
            apply(stored)
            return stored

        return self._modify_in_business(business_id, str(contact_id), change)

    def page_customers(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        page_filter: CustomerPageFilter,
    ) -> list[ContactDocument]:
        matches: list[DocumentFieldMatch] = []
        if page_filter.tag is not None:
            matches.append(field_equals(TAG_FIELD, tag_key(page_filter.tag)))
        if page_filter.vip_only:
            matches.append(field_equals(IS_VIP_FIELD, True))
        if page_filter.blocked_only:
            matches.append(field_equals(IS_BLOCKED_FIELD, True))

        return self._page_in_business(
            business_id,
            (LAST_SEEN_AT_FIELD,),
            window,
            where=DocumentFilter(matches=tuple(matches)),
        )
