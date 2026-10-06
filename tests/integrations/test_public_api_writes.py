"""
The public API's writes: bookings and leads made through a key (their
webhooks fire as for the cabinet's), replayed by Idempotency-Key, and
Zapier's REST-hook subscriptions.
"""

import json

from tests.integrations.integration_shop import DAY, open_integration_shop

LEAD: dict[str, object] = {
    "contact_name": "Ana",
    "contact_phone_number": "555 33 44 55",
    "type": "banquet",
    "details": "Birthday dinner for 20",
    "party_size": 20,
}


def test_a_lead_made_through_the_api_reaches_the_webhooks() -> None:
    with open_integration_shop() as shop:
        shop.add_webhook(["lead.created"])
        key = shop.add_api_key()
        created = shop.api("POST", "/leads", key, LEAD)
        shop.run_jobs()
        posted = list(shop.receivers.posted)
        listed = shop.api("GET", "/leads", key).json()["items"]
        cabinet = shop.get(f"{shop.base}/leads").json()["items"]

    assert created.status_code == 201, created.text
    lead = created.json()
    assert lead["status"] == "new"
    assert lead["contact"]["name"] == "Ana"
    assert lead["contact"]["phone_number"] == "+995555334455"
    assert [item["id"] for item in listed] == [lead["id"]]
    assert [item["id"] for item in cabinet] == [lead["id"]]
    assert len(posted) == 1
    assert json.loads(str(posted[0].body))["data"]["id"] == lead["id"]


def test_a_retried_create_with_the_same_key_makes_one_booking() -> None:
    with open_integration_shop() as shop:
        key = shop.add_api_key()
        body = {
            "contact_name": "Levan",
            "contact_phone_number": "+995 555 44 55 66",
            "resource_id": shop.resource_id,
            "date": DAY,
            "time": "14:00",
            "party_size": 2,
        }
        retry = {"Idempotency-Key": "retry-0000"}  # gitleaks:allow
        first = shop.api("POST", "/bookings", key, body, retry)
        again = shop.api("POST", "/bookings", key, body, retry)
        listed = shop.api("GET", "/bookings", key).json()["items"]

    assert first.status_code == 201, first.text
    assert again.status_code == 201
    assert again.headers.get("Idempotent-Replayed") == "true"
    assert again.json()["id"] == first.json()["id"]
    assert len(listed) == 1
    assert first.json()["source_channel"] == "phone"


def test_a_bad_phone_is_refused() -> None:
    with open_integration_shop() as shop:
        key = shop.add_api_key()
        refused = shop.api(
            "POST", "/leads", key, {**LEAD, "contact_phone_number": "12"}
        )

    assert refused.status_code == 422


def test_zapier_subscribes_and_unsubscribes_a_rest_hook() -> None:
    with open_integration_shop() as shop:
        cabinet_hook = shop.add_webhook()["endpoint"]
        key = shop.add_api_key()
        subscribed = shop.api(
            "POST",
            "/webhooks",
            key,
            {"url": "https://hooks.zapier.com/1", "event_types": ["booking.created"]},
        )
        hook = subscribed.json()["endpoint"]
        shop.book()
        shop.run_jobs()
        posted_to = sorted(str(request.url) for request in shop.receivers.posted)
        not_ours = shop.api("DELETE", f"/webhooks/{cabinet_hook['id']}", key)
        removed = shop.api("DELETE", f"/webhooks/{hook['id']}", key)
        remaining = shop.get(f"{shop.base}/webhooks").json()["items"]

    assert subscribed.status_code == 201, subscribed.text
    assert subscribed.json()["signing_secret"].startswith("whsec_")
    assert hook["origin"] == "api"
    assert posted_to == [
        "https://hooks.example.com/workshop",
        "https://hooks.zapier.com/1",
    ]
    assert not_ours.status_code == 404
    assert removed.status_code == 204
    assert [item["id"] for item in remaining] == [cabinet_hook["id"]]
