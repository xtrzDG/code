"""
End to end over HTTP: a Telegram customer books; the owner tags them,
finds them with the search and in a segment, then blocks them. The
assistant answers nothing they write (their messages still reach the
inbox) and no reminder reaches them; unblocked, they are answered again.
"""

import csv
import io

from fastapi.testclient import TestClient

from tests.e2e.harness import Workshop
from tests.e2e.journeys import (
    BOOKING_REQUEST_RU,
    JsonObject,
    OpenRestaurant,
    open_restaurant,
)
from tests.e2e.telegram_customer import TelegramCustomer

BOOKED: str = "Ваш столик забронирован на 19:00."


def the_customer(client: TestClient, restaurant: OpenRestaurant) -> JsonObject:
    listed = client.get(f"{restaurant.base}/contacts", headers=restaurant.headers)
    assert listed.status_code == 200, listed.text
    [customer] = [
        item for item in listed.json()["items"] if "telegram" in item["channels"]
    ]
    return dict(customer)


def customer_texts(
    client: TestClient, restaurant: OpenRestaurant, conversation_id: str
) -> list[str]:
    transcript = client.get(
        f"{restaurant.base}/conversations/{conversation_id}/messages?limit=100",
        headers=restaurant.headers,
    )
    assert transcript.status_code == 200, transcript.text
    return [
        str(item["text"])
        for item in transcript.json()["items"]
        if item["author"] == "customer"
    ]


def test_the_owner_tags_finds_segments_and_blocks_a_customer(
    workshop: Workshop,
) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    base, headers = restaurant.base, restaurant.headers
    customer = TelegramCustomer(workshop, restaurant)
    assert customer.writes(BOOKING_REQUEST_RU)[-1].endswith(BOOKED)
    contact_id = str(the_customer(client, restaurant)["id"])

    card = client.patch(
        f"{base}/contacts/{contact_id}/card",
        json={"add_tags": ["Regular"], "is_vip": True},
        headers=headers,
    )
    assert card.status_code == 200, card.text
    assert (card.json()["tags"], card.json()["is_vip"]) == (["Regular"], True)
    standing = client.get(f"{base}/contacts/{contact_id}/standing", headers=headers)
    assert standing.json()["standing"] == "new"
    found = client.get(f"{base}/search", params={"q": contact_id}, headers=headers)
    assert [item["id"] for item in found.json()["customers"]] == [contact_id]
    assert (
        client.get(f"{base}/search", params={"q": ""}, headers=headers).status_code
        == 422
    )

    segment = client.post(
        f"{base}/customer-segments",
        json={"name": "Regulars", "rules": {"tag": "regular", "vip_only": True}},
        headers=headers,
    )
    assert segment.status_code == 201, segment.text
    segment_path = f"{base}/customer-segments/{segment.json()['id']}"
    members = client.get(f"{segment_path}/members", headers=headers).json()
    assert [item["id"] for item in members["items"]] == [contact_id]
    exported = client.get(f"{segment_path}/export?language=en", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert rows[0][0] == "Customer ID"
    assert [row[0] for row in rows[1:]] == [contact_id]

    blocked = client.put(
        f"{base}/contacts/{contact_id}/blocking",
        json={"is_blocked": True},
        headers=headers,
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["is_blocked"] is True

    # The customer writes; the assistant stays silent, the inbox has it.
    assert customer.writes("Здравствуйте, вы тут?") == []
    detail = client.get(f"{base}/contacts/{contact_id}", headers=headers).json()
    assert detail["contact"]["is_blocked"] is True
    assert detail["blocked_at"] is not None
    [conversation_id] = [item["id"] for item in detail["conversations"]]
    assert "Здравствуйте, вы тут?" in customer_texts(
        client, restaurant, conversation_id
    )
    # A blocked customer belongs to no segment.
    assert client.get(f"{segment_path}/members", headers=headers).json()["items"] == []

    # The visit comes due; no reminder reaches them.
    received = len(customer.received())
    worker = workshop.container.gateways.background_worker()
    for _ in range(36):
        workshop.clock.advance(60 * 60)
        assert worker.run_once().failures == 0
    assert len(customer.received()) == received

    unblocked = client.put(
        f"{base}/contacts/{contact_id}/blocking",
        json={"is_blocked": False},
        headers=headers,
    )
    assert unblocked.json()["is_blocked"] is False
    assert customer.writes("Спасибо!") != []
