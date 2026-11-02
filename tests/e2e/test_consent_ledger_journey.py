"""
End to end over HTTP: the consent ledger keeps every marketing consent a
Telegram customer gives and takes back (CONS-02), with where it happened,
the wording's version and language, and who recorded it. The customer's
export shows the trail; after their erasure the ledger still proves it, by
the erased contact's id alone.
"""

from typing import Any

from fastapi.testclient import TestClient

from app.schemas.constants.consent_records import (
    ConsentEvent,
    ConsentEventSource,
    ConsentPurpose,
)
from app.schemas.constants.marketing_consent import CURRENT_MARKETING_CONSENT_TEXT
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from tests.e2e.harness import Workshop
from tests.e2e.journeys import BOOKING_REQUEST_RU, OpenRestaurant, open_restaurant
from tests.e2e.telegram_customer import CUSTOMER_CHAT, TelegramCustomer


def the_customer(client: TestClient, restaurant: OpenRestaurant) -> str:
    listed = client.get(f"{restaurant.base}/contacts", headers=restaurant.headers)
    assert listed.status_code == 200, listed.text
    [customer] = [
        item for item in listed.json()["items"] if "telegram" in item["channels"]
    ]
    return str(customer["id"])


def record_in_person(
    client: TestClient, restaurant: OpenRestaurant, contact_id: str, given: bool
) -> None:
    card = client.patch(
        f"{restaurant.base}/contacts/{contact_id}/card",
        json={"marketing_consent": given},
        headers=restaurant.headers,
    )
    assert card.status_code == 200, card.text


def ledger(
    workshop: Workshop, restaurant: OpenRestaurant, contact_id: str
) -> list[ConsentRecordDocument]:
    container = workshop.container
    with container.utilities.storage_scope().platform_wide():
        return container.repositories.consent_record_repo().list_by_contact(
            BusinessId(restaurant.business_id), ContactId(contact_id)
        )


def trail(entries: list[Any]) -> list[tuple[str, str]]:
    return [(str(entry["event"]), str(entry["source"])) for entry in entries]


def test_the_ledger_keeps_every_consent_and_outlives_the_erasure(
    workshop: Workshop,
) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    customer = TelegramCustomer(workshop, restaurant)
    customer.writes(BOOKING_REQUEST_RU)
    contact_id = the_customer(client, restaurant)

    # Agreed in person, said STOP in the chat, agreed in person again.
    record_in_person(client, restaurant, contact_id, True)
    record_in_person(client, restaurant, contact_id, True)
    customer.writes("СТОП")
    record_in_person(client, restaurant, contact_id, True)

    exported = client.get(
        f"{restaurant.base}/contacts/{contact_id}/export", headers=restaurant.headers
    )
    assert exported.status_code == 200, exported.text
    records = exported.json()["records"]["consent_records"]
    assert trail(records) == [
        ("given", "in_person"),
        ("withdrawn", "stop"),
        ("given", "in_person"),
    ]
    given, stopped, _ = records
    assert given["recorded_by"] == restaurant.owner_id
    assert given["text_version"] == CURRENT_MARKETING_CONSENT_TEXT.value
    assert given["purpose"] == ConsentPurpose.MARKETING.value
    assert (stopped["channel"], stopped["language"]) == ("telegram", "ru")
    assert stopped["conversation_id"] is not None
    assert stopped["recorded_by"] is None

    erased = client.delete(
        f"{restaurant.base}/contacts/{contact_id}", headers=restaurant.headers
    )
    assert erased.status_code == 204, erased.text

    kept = ledger(workshop, restaurant, contact_id)
    assert [(entry.event, entry.source) for entry in kept] == [
        (ConsentEvent.GIVEN, ConsentEventSource.IN_PERSON),
        (ConsentEvent.WITHDRAWN, ConsentEventSource.STOP),
        (ConsentEvent.GIVEN, ConsentEventSource.IN_PERSON),
        (ConsentEvent.WITHDRAWN, ConsentEventSource.ERASURE),
    ]
    assert [str(entry.id) for entry in kept[:3]] == [
        str(record["id"]) for record in records
    ]
    # Pseudonymous proof: the contact's id, never the customer's account.
    assert all(str(CUSTOMER_CHAT) not in entry.model_dump_json() for entry in kept)
