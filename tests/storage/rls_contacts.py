"""Contacts of two businesses saved for the row-level security tests."""

from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.storage.builders import COUNTRY_SAMPLES, build_contact
from tests.storage.conftest import PostgresCollectionFactory

GEORGIA, ISRAEL, EMIRATES, JAPAN = COUNTRY_SAMPLES[0:4]


def save_two_businesses_contacts(
    postgres_collections: PostgresCollectionFactory,
) -> tuple[BusinessId, BusinessId, ContactDocument, ContactDocument]:
    contacts = postgres_collections(ContactDocument, "contacts")
    first_business_id, second_business_id = BusinessId(), BusinessId()
    first_contact = build_contact(GEORGIA, first_business_id)
    second_contact = build_contact(ISRAEL, second_business_id)
    contacts.upsert(str(first_contact.id), first_contact)
    contacts.upsert(str(second_contact.id), second_contact)
    return first_business_id, second_business_id, first_contact, second_contact
