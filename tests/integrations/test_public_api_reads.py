"""
The public API's reads: the key's business only, each record kind behind
its scope, every read in the owner's audit log, and a per-key limit.
"""

from tests.integrations.integration_shop import (
    open_integration_shop,
    open_other_business,
)


def test_bookings_are_read_with_their_customer_and_source() -> None:
    with open_integration_shop() as shop:
        booking = shop.book()
        key = shop.add_api_key(["bookings:read"])
        page = shop.api("GET", "/bookings", key)
        one = shop.api("GET", f"/bookings/{booking['id']}", key)
        audit = shop.get(f"{shop.base}/audit-log").json()["items"]

    assert page.status_code == 200, page.text
    assert [item["id"] for item in page.json()["items"]] == [booking["id"]]
    assert page.json()["next_cursor"] is None
    record = one.json()
    assert record["contact"]["name"] == "Nino"
    assert record["resource"]["name"] == "Window table"
    assert record["timezone"] == "Asia/Tbilisi"
    assert record["starts_at"].startswith("2026-10-06T13:00:00")
    api_reads = [entry for entry in audit if entry["entity"] == "api_booking"]
    assert api_reads
    assert {entry["action"] for entry in api_reads} == {"view"}
    assert {entry["entity_id"] for entry in api_reads} == {
        shop.get(f"{shop.base}/api-keys").json()["items"][0]["id"]
    }


def test_a_key_without_the_scope_is_refused() -> None:
    with open_integration_shop() as shop:
        key = shop.add_api_key(["leads:read"])
        bookings = shop.api("GET", "/bookings", key)
        contacts = shop.api("GET", "/contacts", key)
        create = shop.api(
            "POST",
            "/leads",
            key,
            {"contact_name": "Ana", "type": "banquet", "details": "Birthday for 20"},
        )
        subscribe = shop.api(
            "POST",
            "/webhooks",
            key,
            {"url": "https://hooks.zapier.com/1", "event_types": ["lead.created"]},
        )

    for refused, scope in (
        (bookings, "bookings:read"),
        (contacts, "contacts:read"),
        (create, "leads:write"),
        (subscribe, "webhooks:manage"),
    ):
        assert refused.status_code == 403, refused.text
        assert refused.json()["reasons"][0]["code"] == "missing_scope"
        assert refused.json()["reasons"][0]["details"] == [scope]


def test_a_key_cannot_read_another_business() -> None:
    with open_integration_shop() as shop:
        other = open_other_business(shop.workshop)
        theirs = other.book()
        their_contact = theirs["contact_id"]
        key = shop.add_api_key()
        bookings = shop.api("GET", "/bookings", key)
        booking = shop.api("GET", f"/bookings/{theirs['id']}", key)
        contact = shop.api("GET", f"/contacts/{their_contact}", key)
        contacts = shop.api("GET", "/contacts", key)

    assert bookings.json()["items"] == []
    assert booking.status_code == 404
    assert contact.status_code == 404
    assert their_contact not in str(contacts.json())


def test_contacts_and_conversations_are_listed() -> None:
    with open_integration_shop() as shop:
        shop.book()
        key = shop.add_api_key()
        contacts = shop.api("GET", "/contacts", key).json()["items"]
        conversations = shop.api("GET", "/conversations?limit=5", key)
        missing = shop.api("GET", "/conversations/conversation_unknown", key)

    assert [contact["name"] for contact in contacts] == ["Nino"]
    assert contacts[0]["phone_number"] == "+995555112233"
    assert conversations.status_code == 200, conversations.text
    assert conversations.json()["items"] == []
    assert missing.status_code in (404, 422)


def test_each_key_has_its_own_request_limit() -> None:
    with open_integration_shop({"PUBLIC_API_REQUESTS_PER_MINUTE": "3"}) as shop:
        first = shop.add_api_key(name="First")
        second = shop.add_api_key(name="Second")
        answers = [shop.api("GET", "/me", first).status_code for _ in range(4)]
        other_key = shop.api("GET", "/me", second)
        limited = shop.api("GET", "/me", first)
        shop.workshop.clock.advance(121)
        later = shop.api("GET", "/me", first)

    assert answers == [200, 200, 200, 429]
    assert other_key.status_code == 200
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    assert later.status_code == 200
