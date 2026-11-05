"""
The customer routes over HTTP on the demo restaurant: the staff-safe list,
the customer settings, the card's validation, the list filters, the search
and segments (the owner-only refusals are in the authorization matrix).
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

import pytest

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.platform.authorization_world import (
    DEMO_OWNER_EMAIL,
    DEMO_RESTAURANT,
    DEMO_STAFF_PHONE,
)

type JsonObject = dict[str, Any]


@dataclass(frozen=True)
class DemoRestaurant:
    workshop: Workshop
    base: str
    owner: dict[str, str]
    staff: dict[str, str]

    def get(
        self, path: str, headers: dict[str, str] | None = None, **params: str
    ) -> Any:
        response = self.workshop.client.get(
            f"{self.base}{path}", params=params, headers=headers or self.owner
        )
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture(scope="module")
def demo() -> Iterator[DemoRestaurant]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "SEED_DEMO_DATA": "true"})
    with workshop.client:
        owner = bearer(workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])
        staff = bearer(workshop.sign_in_with_phone(DEMO_STAFF_PHONE)[0])
        businesses = cast(
            list[JsonObject],
            workshop.client.get("/v1/businesses", headers=owner).json(),
        )
        business = next(item for item in businesses if item["name"] == DEMO_RESTAURANT)
        yield DemoRestaurant(
            workshop=workshop,
            base=f"/v1/businesses/{business['id']}",
            owner=owner,
            staff=staff,
        )


def first_customer_with_phone(demo: DemoRestaurant) -> JsonObject:
    rows = cast(list[JsonObject], demo.get("/contacts", limit="50")["items"])
    return next(row for row in rows if row["phone_number"] is not None)


def test_staff_see_masked_phones_until_the_owner_allows_them(
    demo: DemoRestaurant,
) -> None:
    client = demo.workshop.client
    customer = first_customer_with_phone(demo)

    masked = demo.get(f"/contacts/{customer['id']}", headers=demo.staff)["contact"]
    assert masked["phone_number"] is None
    assert masked["is_phone_masked"] is True
    assert str(masked["masked_phone_number"]).endswith(customer["phone_number"][-2:])

    allowed = client.put(
        f"{demo.base}/customer-settings",
        json={"staff_sees_phone_numbers": True},
        headers=demo.owner,
    )
    assert allowed.status_code == 200, allowed.text
    seen = demo.get(f"/contacts/{customer['id']}", headers=demo.staff)["contact"]
    assert seen["phone_number"] == customer["phone_number"]
    assert (
        demo.get("/customer-settings", headers=demo.staff)["staff_sees_phone_numbers"]
        is True
    )
    client.put(
        f"{demo.base}/customer-settings",
        json={"staff_sees_phone_numbers": False},
        headers=demo.owner,
    )


def test_the_card_refuses_bad_tags(demo: DemoRestaurant) -> None:
    customer = first_customer_with_phone(demo)
    path = f"{demo.base}/contacts/{customer['id']}/card"
    client = demo.workshop.client

    for body in (
        {"add_tags": [" spaced "]},
        {"add_tags": ["x" * 33]},
        {"add_tags": [f"tag {index}" for index in range(21)]},
    ):
        refused = client.patch(path, json=body, headers=demo.owner)
        assert refused.status_code == 422, (body, refused.text)

    accepted = client.patch(
        path, json={"add_tags": ["Window seat"], "is_vip": True}, headers=demo.staff
    )
    assert accepted.status_code == 200, accepted.text
    assert "Window seat" in accepted.json()["known_tags"]


def test_the_list_filters_by_tag_and_flag(demo: DemoRestaurant) -> None:
    customer = first_customer_with_phone(demo)
    demo.workshop.client.patch(
        f"{demo.base}/contacts/{customer['id']}/card",
        json={"add_tags": ["Birthday"], "is_vip": True},
        headers=demo.owner,
    )

    tagged = demo.get("/contacts", tag="birthday")["items"]
    vips = demo.get("/contacts", filter="vip")["items"]
    refused = demo.workshop.client.get(
        f"{demo.base}/contacts", params={"filter": "favourite"}, headers=demo.owner
    )

    assert [row["id"] for row in tagged] == [customer["id"]]
    assert customer["id"] in [row["id"] for row in vips]
    assert all(row["is_vip"] for row in vips)
    assert refused.status_code == 422


def test_the_search_groups_hits_and_refuses_empty_text(demo: DemoRestaurant) -> None:
    customer = first_customer_with_phone(demo)
    client = demo.workshop.client
    name = str(customer["name"])

    found = demo.get("/search", q=name)
    blank = client.get(f"{demo.base}/search", params={"q": "  "}, headers=demo.owner)
    long = client.get(
        f"{demo.base}/search", params={"q": "x" * 101}, headers=demo.owner
    )
    missing = client.get(f"{demo.base}/search", headers=demo.owner)

    assert customer["id"] in [row["id"] for row in found["customers"]]
    assert set(found) == {"customers", "conversations", "bookings"}
    assert [blank.status_code, long.status_code, missing.status_code] == [422] * 3


def test_segments_preview_save_and_delete(demo: DemoRestaurant) -> None:
    client = demo.workshop.client
    path = f"{demo.base}/customer-segments"

    refused = client.post(
        path,
        json={"name": "Odd", "rules": {"min_bookings": 3, "max_bookings": 1}},
        headers=demo.owner,
    )
    preview = client.post(
        path + "/preview", json={"min_bookings": 1}, headers=demo.owner
    )
    created = client.post(
        path,
        json={"name": "Booked once", "rules": {"min_bookings": 1}},
        headers=demo.owner,
    )

    assert refused.status_code == 422
    assert preview.status_code == 200, preview.text
    assert preview.json()["is_count_exact"] is True
    assert created.status_code == 201, created.text
    segment_id = created.json()["id"]
    members = demo.get(f"/customer-segments/{segment_id}/members")["items"]
    assert len(members) == min(preview.json()["member_count"], 50)
    deleted = client.delete(f"{path}/{segment_id}", headers=demo.owner)
    assert deleted.status_code == 204
    gone = client.get(f"{path}/{segment_id}/members", headers=demo.owner)
    assert gone.status_code == 404
