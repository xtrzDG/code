"""
Every document of one business in keyset pages, in the order they were
first written (`page_in_write_order`, the pages of a full export): no
document twice, none of another business, one written during the walk at
its end, on the in-memory and the Postgres storage alike.
"""

import pytest

from app.repositories.conversation_repositories import ContactRepository
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.strings import ListItemKey
from tests.storage.builders import COUNTRY_SAMPLES, build_contact
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")


def walk(
    repo: ContactRepository, business_id: BusinessId, limit: int
) -> list[list[ContactId]]:
    pages: list[list[ContactId]] = []
    after: KeysetPosition | None = None
    while True:
        page: list[ContactDocument] = repo.page_in_write_order(
            business_id, KeysetSlice(after=after, limit=KeysetReadLimit(limit))
        )
        if page:
            pages.append([contact.id for contact in page])
        if len(page) < limit:
            return pages
        after = KeysetPosition(sort_values=(), item_key=ListItemKey(str(page[-1].id)))


def test_pages_hold_each_document_of_the_business_once_in_write_order(
    collections: CollectionFactory,
) -> None:
    repo = ContactRepository(collections(ContactDocument, "contacts"))
    business, neighbour = BusinessId(), BusinessId()
    written: list[ContactId] = []
    for index in range(7):
        contact = build_contact(COUNTRY_SAMPLES[index % len(COUNTRY_SAMPLES)], business)
        repo.save(contact)
        written.append(contact.id)
        repo.save(build_contact(COUNTRY_SAMPLES[0], neighbour))

    pages = walk(repo, business, 3)

    assert [len(page) for page in pages] == [3, 3, 1]
    assert [contact_id for page in pages for contact_id in page] == written
    assert walk(repo, BusinessId(), 3) == []


def test_a_document_written_during_the_walk_comes_at_its_end(
    collections: CollectionFactory,
) -> None:
    repo = ContactRepository(collections(ContactDocument, "contacts"))
    business = BusinessId()
    first = build_contact(COUNTRY_SAMPLES[0], business)
    repo.save(first)
    [page] = [repo.page_in_write_order(business, KeysetSlice(limit=KeysetReadLimit(5)))]
    late = build_contact(COUNTRY_SAMPLES[0], business)
    repo.save(late)
    # A changed document keeps its place: its first write decides.
    repo.save(first.model_copy(update={"name": first.name}))

    rest = repo.page_in_write_order(
        business,
        KeysetSlice(
            after=KeysetPosition(sort_values=(), item_key=ListItemKey(str(first.id))),
            limit=KeysetReadLimit(5),
        ),
    )

    assert [contact.id for contact in page] == [first.id]
    assert [contact.id for contact in rest] == [late.id]
