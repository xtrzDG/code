"""Share links, the hosted chat page's address and its public configuration."""

from tests.e2e.harness import Workshop
from tests.sharing.conftest import CABINET_BASE_URL
from tests.sharing.sharing_steps import (
    add_staff,
    create_business,
    set_slug,
    share_links,
)

OWNER_PHONE: str = "+995 555 11 22 33"
OTHER_OWNER_PHONE: str = "+995 555 44 55 66"
STAFF_PHONE: str = "+995 555 77 88 99"


def test_the_first_share_gives_the_business_an_address_from_its_name(
    workshop: Workshop,
) -> None:
    business = create_business(workshop, OWNER_PHONE, "Café Батуми")

    first = share_links(workshop, business)
    again = share_links(workshop, business, source="qr")

    assert first["slug"] == "cafe-batumi"
    assert first["hosted_chat_url"] == f"{CABINET_BASE_URL}/c/cafe-batumi"
    assert first["links"] == [
        {
            "kind": "hosted_chat",
            "url": f"{CABINET_BASE_URL}/c/cafe-batumi",
            "label": "app.workshop.example/c/cafe-batumi",
            "gap": None,
        }
    ]
    assert again["slug"] == "cafe-batumi"
    assert again["source"] == "qr"
    assert again["hosted_chat_url"] == f"{CABINET_BASE_URL}/c/cafe-batumi?src=qr"


def test_a_second_business_of_the_same_name_gets_the_next_address(
    workshop: Workshop,
) -> None:
    first = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    second = create_business(workshop, OTHER_OWNER_PHONE, "Cafe Batumi")

    assert share_links(workshop, first)["slug"] == "cafe-batumi"
    assert share_links(workshop, second)["slug"] == "cafe-batumi-2"


def test_staff_see_the_links_but_only_owners_change_the_address(
    workshop: Workshop,
) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    staff = add_staff(workshop, business, STAFF_PHONE)

    assert share_links(workshop, business, headers=staff)["slug"] == "cafe-batumi"
    refused = workshop.client.put(
        f"{business.base}/public-slug", json={"slug": "batumi"}, headers=staff
    )
    assert refused.status_code == 403


def test_an_owner_renames_the_address_and_old_qr_codes_keep_working(
    workshop: Workshop,
) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    share_links(workshop, business)

    renamed = set_slug(workshop, business, "batumi-seaside")

    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["slug"] == "batumi-seaside"
    old = workshop.client.get("/v1/public/chat/cafe-batumi").json()
    new = workshop.client.get("/v1/public/chat/batumi-seaside").json()
    assert old["business_id"] == new["business_id"] == business.business_id
    # The page moves visitors of the old address to the current one.
    assert old["slug"] == "batumi-seaside"
    back = set_slug(workshop, business, "cafe-batumi")
    assert back.status_code == 200
    assert back.json()["slug"] == "cafe-batumi"


def test_an_address_another_business_ever_had_is_refused(workshop: Workshop) -> None:
    first = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    second = create_business(workshop, OTHER_OWNER_PHONE, "Seaside")
    share_links(workshop, first)
    assert set_slug(workshop, first, "batumi-seaside").status_code == 200

    taken = set_slug(workshop, second, "cafe-batumi")

    assert taken.status_code == 409
    assert taken.json()["reasons"][0]["code"] == "slug_taken"
    assert share_links(workshop, second)["slug"] == "seaside"


def test_reserved_and_malformed_addresses_are_refused(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")

    reserved = set_slug(workshop, business, "privacy")
    generated = set_slug(workshop, business, "chat-0b6c2f5e")
    malformed = set_slug(workshop, business, "Café Batumi")

    assert reserved.status_code == 422
    assert reserved.json()["reasons"][0]["code"] == "slug_reserved"
    assert generated.json()["reasons"][0]["code"] == "slug_reserved"
    assert malformed.status_code == 422


def test_connected_channels_are_listed_with_their_links(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    connected = workshop.client.put(
        f"{business.base}/channels/telegram",
        json={"bot_token": "7770001:AAHbusiness_bot_token_for_sharing_tests_01"},
        headers=business.owner,
    )
    assert connected.status_code == 200, connected.text

    links = share_links(workshop, business, source="qr")["links"]

    assert links[1] == {
        "kind": "telegram",
        "url": "https://t.me/workshop_bot?start=src_qr",
        "label": "@workshop_bot",
        "gap": None,
    }


def test_the_public_page_config_names_no_secret(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    share_links(workshop, business)

    response = workshop.client.get("/v1/public/chat/cafe-batumi")

    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == "noindex"
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["business_name"] == "Cafe Batumi"
    assert body["is_enabled"] is False
    assert body["api_base_url"] == "https://api.workshop.example"
    assert body["widget_script_url"] == "https://api.workshop.example/widget.js"
    assert body["privacy_url"] == f"{CABINET_BASE_URL}/c/cafe-batumi/privacy"
    assert set(body) == {
        "business_id",
        "slug",
        "business_name",
        "is_enabled",
        "default_language",
        "languages",
        "accent_color",
        "position",
        "api_base_url",
        "widget_script_url",
        "privacy_url",
        "conversation_retention_days",
        "llm_turn_retention_days",
        "timezone",
        "hours",
        "address",
        "maps_url",
        "takes_bookings",
        "booking_url",
        "powered_by_url",
    }
    # "Powered by" names only the platform's site and the business's code.
    assert body["powered_by_url"].startswith(f"{CABINET_BASE_URL}/?ref=")
    # The privacy notice names the business's own periods (the defaults).
    assert (body["conversation_retention_days"], body["llm_turn_retention_days"]) == (
        730,
        30,
    )


def test_a_business_without_an_address_is_found_by_its_id(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")

    by_id = workshop.client.get(f"/v1/public/chat/{business.business_id}")

    assert by_id.status_code == 200
    assert by_id.json()["slug"] is None
    assert by_id.json()["privacy_url"] == (
        f"{CABINET_BASE_URL}/c/{business.business_id}/privacy"
    )


def test_unknown_addresses_are_not_found(workshop: Workshop) -> None:
    for address in [
        "nobody-here",
        "business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01",
        "%20",
    ]:
        response = workshop.client.get(f"/v1/public/chat/{address}")
        assert response.status_code == 404, address
