"""
A booking made in the cabinet reaches the business's webhook: one signed
POST the receiver can verify with the secret it was shown once, the
booking with its customer in the body, and the delivery in the log.
"""

import json

from tests.integrations.integration_shop import open_integration_shop
from tests.integrations.webhook_receivers import is_valid_signature


def test_a_new_booking_is_posted_signed_to_the_webhook() -> None:
    with open_integration_shop() as shop:
        created = shop.add_webhook(["booking.created", "booking.cancelled"])
        listed = shop.get(f"{shop.base}/webhooks").json()
        booking = shop.book()
        shop.run_jobs()
        posted = list(shop.receivers.posted)
        log = shop.deliveries(created["endpoint"]["id"])
        now_seconds = shop.workshop.clock.wall_clock.now_unix() // 1_000_000

    secret = str(created["signing_secret"])
    assert secret.startswith("whsec_")
    assert secret not in json.dumps(listed)
    assert listed["items"][0]["secret_hint"] == secret[-4:]
    assert [str(request.event_type) for request in posted] == ["booking.created"]
    request = posted[0]
    assert is_valid_signature(
        secret, str(request.signature), str(request.body), int(now_seconds)
    )
    event = json.loads(str(request.body))
    assert event["type"] == "booking.created"
    assert event["business_id"] == shop.business_id
    assert event["data"]["id"] == booking["id"]
    assert event["data"]["contact"]["name"] == "Nino"
    assert event["data"]["contact"]["phone_number"] == "+995555112233"
    assert str(request.event_id) == event["id"]
    assert [item["status"] for item in log] == ["delivered"]
    assert log[0]["attempts"] == 1
    assert log[0]["last_status_code"] == 200


def test_events_the_webhook_did_not_choose_are_not_posted() -> None:
    with open_integration_shop() as shop:
        shop.add_webhook(["lead.created"])
        shop.book()
        shop.run_jobs()
        posted = list(shop.receivers.posted)

    assert posted == []
