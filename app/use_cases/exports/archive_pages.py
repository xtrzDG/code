"""
The collections of a full export as bounded pages: each read a keyset page
of 1,000 documents at a time in the order they were first written, so the
worker holds one page of a collection, never the collection.
"""

from collections.abc import Iterable, Iterator, Sequence

from base_pydantic_schemas import BaseDocument

from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.exports.business_rows import is_erased
from app.use_cases.exports.people_rows import is_test_only
from app.use_cases.shared.document_pages import pages_in_write_order

type DocumentPages = Iterable[Sequence[BaseDocument]]


def customer_pages(
    contact_repo: BusinessDocumentPagesContract[ContactDocument],
    business_id: BusinessId,
) -> Iterator[list[ContactDocument]]:
    """The business's customers: erased ones and test-chat contacts left out."""

    for page in pages_in_write_order(
        contact_repo, business_id, lambda contact: str(contact.id)
    ):
        yield [
            contact
            for contact in page
            if not is_erased(contact) and not is_test_only(contact)
        ]


def conversation_pages(
    conversation_repo: BusinessDocumentPagesContract[ConversationDocument],
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
) -> Iterator[list[ConversationDocument]]:
    """The conversations, those of erased customers left out (one read each page)."""

    for page in pages_in_write_order(
        conversation_repo, business_id, lambda conversation: str(conversation.id)
    ):
        contact_ids: list[ContactId] = list(
            dict.fromkeys(conversation.contact_id for conversation in page)
        )
        contacts: dict[ContactId, ContactDocument] = contact_repo.get_many(
            business_id, contact_ids
        )
        yield [
            conversation
            for conversation in page
            if not is_erased(contacts.get(conversation.contact_id))
        ]


def single_page(documents: Sequence[BaseDocument]) -> DocumentPages:
    """A small collection (the business itself, its resources) as one page."""

    return [documents]
