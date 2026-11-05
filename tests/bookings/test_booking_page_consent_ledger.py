"""
The marketing box of a guest's booking page writes the consent ledger
(CONS-02): ticking is a GIVEN entry, unticking a WITHDRAWN one, each with
the page's booking, the chat the booking came from, the wording's version,
the language the page showed it in and the guest's network; ticking again
writes nothing. The ledger refuses to change or remove an entry.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.consent_record_repository import ConsentRecordRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.consent_records import (
    ConsentEvent,
    ConsentEventSource,
    ConsentPurpose,
)
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.utilities.storage.consent_collections import CONSENT_COLLECTIONS
from tests.bookings.manage_journey import BookedTable, book_a_table
from tests.bookings.test_booking_page_consent import TEXT_VERSION, tick
from tests.e2e.harness import Workshop


def ledger(workshop: Workshop, booked: BookedTable) -> list[ConsentRecordDocument]:
    """The consent ledger's entries of the booking's guest, oldest first."""

    restaurant = booked.restaurant
    [customer] = workshop.client.get(
        f"{restaurant.base}/contacts", headers=restaurant.headers
    ).json()["items"]
    business_id = BusinessId(restaurant.business_id)
    container = workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        return container.repositories.consent_record_repo().list_by_contact(
            business_id, ContactId(str(customer["id"]))
        )


def test_each_tick_and_untick_is_an_entry_with_its_proof(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    tick(workshop, booked, True)
    tick(workshop, booked, True)
    tick(workshop, booked, False)

    given, withdrawn = ledger(workshop, booked)
    assert (given.event, withdrawn.event) == (
        ConsentEvent.GIVEN,
        ConsentEvent.WITHDRAWN,
    )
    for entry in (given, withdrawn):
        assert entry.source is ConsentEventSource.BOOKING_PAGE
        assert entry.purpose is ConsentPurpose.MARKETING
        assert str(entry.text_version) == TEXT_VERSION
        assert str(entry.language) == "ru"
        assert entry.channel is ChannelKind.WEB_CHAT
        assert entry.booking_id is not None
        assert entry.client_ip_address is not None
        assert entry.recorded_by is None
    assert given.contact_id == withdrawn.contact_id
    assert int(given.created_at) <= int(withdrawn.created_at)


def test_the_ledger_is_declared_append_only() -> None:
    [definition] = CONSENT_COLLECTIONS

    assert definition.is_append_only


def test_appending_the_same_entry_twice_keeps_the_first() -> None:
    repo = ConsentRecordRepository(
        InMemoryDocumentCollectionAdapter(ConsentRecordDocument)
    )
    entry = ConsentRecordDocument(
        business_id=BusinessId(),
        contact_id=ContactId(),
        event=ConsentEvent.GIVEN,
        source=ConsentEventSource.IN_PERSON,
    )
    repo.append(entry)

    repo.append(entry.model_copy(update={"event": ConsentEvent.WITHDRAWN}))

    assert repo.list_by_contact(entry.business_id, entry.contact_id) == [entry]


def test_an_entry_never_names_the_customer() -> None:
    # Pseudonymous proof that outlives an erasure: the contact's id only.
    fields = set(ConsentRecordDocument.model_fields)

    assert {"name", "phone_number", "channel_user_id", "text"}.isdisjoint(fields)
