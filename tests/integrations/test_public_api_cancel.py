"""
`POST /v1/public-api/bookings/{booking_id}/cancel`: a key with
`bookings:write` cancels a booking of its business as staff would in the
cabinet; the answer is the cancelled booking, again for a cancelled one,
retried by Idempotency-Key, and another business's booking is not found.
"""

from tests.integrations.integration_shop import (
    open_integration_shop,
    open_other_business,
)


def test_a_key_cancels_a_booking_of_its_business() -> None:
    with open_integration_shop() as shop:
        booking = shop.book()
        key = shop.add_api_key()
        cancelled = shop.api("POST", f"/bookings/{booking['id']}/cancel", key)
        again = shop.api("POST", f"/bookings/{booking['id']}/cancel", key)
        read = shop.api("GET", f"/bookings/{booking['id']}", key)
        audit = shop.get(f"{shop.base}/audit-log").json()["items"]

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["id"] == booking["id"]
    assert cancelled.json()["status"] == "cancelled"
    # Cancelling a cancelled booking changes nothing and answers the same.
    assert again.status_code == 200, again.text
    assert again.json() == cancelled.json()
    assert read.json()["status"] == "cancelled"
    changes = [
        entry
        for entry in audit
        if entry["entity"] == "booking" and entry["entity_id"] == booking["id"]
    ]
    assert changes, audit


def test_a_retried_cancellation_replays_its_answer() -> None:
    with open_integration_shop() as shop:
        booking = shop.book()
        key = shop.add_api_key()
        retry = {"Idempotency-Key": "cancel-0000"}  # gitleaks:allow
        first = shop.api("POST", f"/bookings/{booking['id']}/cancel", key, None, retry)
        again = shop.api("POST", f"/bookings/{booking['id']}/cancel", key, None, retry)

    assert first.status_code == 200, first.text
    assert again.status_code == 200
    assert again.headers.get("Idempotent-Replayed") == "true"
    assert again.json() == first.json()


def test_another_business_booking_is_not_found_and_stays() -> None:
    with open_integration_shop() as shop:
        other = open_other_business(shop.workshop)
        theirs = other.book()
        key = shop.add_api_key()
        refused = shop.api("POST", f"/bookings/{theirs['id']}/cancel", key)
        unknown = shop.api("POST", "/bookings/not-a-booking/cancel", key)
        kept = other.api("GET", f"/bookings/{theirs['id']}", other.add_api_key())

    assert refused.status_code == 404
    assert unknown.status_code == 404
    assert kept.json()["status"] == "confirmed"


def test_a_key_without_bookings_write_cannot_cancel() -> None:
    with open_integration_shop() as shop:
        booking = shop.book()
        reader = shop.add_api_key(["bookings:read"], name="Reader")
        refused = shop.api("POST", f"/bookings/{booking['id']}/cancel", reader)
        kept = shop.api("GET", f"/bookings/{booking['id']}", reader)

    assert refused.status_code == 403
    assert kept.json()["status"] == "confirmed"
