"""
A brand through its API, on the brand matrix's world (demo restaurant B
and its second location C, a regional manager of C, a co-owner): the
combined dashboard, a location made from another one, shared knowledge
overridden in one location, and what the switcher reads from /v1/me.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from tests.platform.brand_matrix_world import BrandWorld, open_brand_world

type Json = dict[str, Any]


@pytest.fixture(scope="module")
def brand() -> Iterator[BrandWorld]:
    with open_brand_world() as opened:
        yield opened


def read(brand: BrandWorld, path: str, headers: dict[str, str]) -> Any:
    response = brand.world.workshop.client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def location_ids(dashboard: Json) -> set[str]:
    return {str(row["location"]["business_id"]) for row in dashboard["locations"]}


def test_the_dashboard_adds_up_every_location_for_the_owner(brand: BrandWorld) -> None:
    world = brand.world
    dashboard: Json = read(
        brand, f"/v1/brands/{brand.brand_id}/dashboard", world.owner_b
    )

    assert {world.business_b, brand.location_c} <= location_ids(dashboard)
    assert dashboard["viewer_role"] == "brand_owner"
    for row in dashboard["locations"]:
        assert row["is_locked"] is False
        assert row["inbox"] is not None
        assert row["value"] is not None


def test_a_regional_manager_sees_only_the_assigned_location(brand: BrandWorld) -> None:
    dashboard: Json = read(
        brand, f"/v1/brands/{brand.brand_id}/dashboard", brand.manager
    )

    assert location_ids(dashboard) == {brand.location_c}
    assert dashboard["viewer_role"] == "regional_manager"
    # Customer sources are the owners' (they name where customers came from).
    assert all(row["sources"] is None for row in dashboard["locations"])


def test_the_switcher_groups_reached_locations_under_the_brand(
    brand: BrandWorld,
) -> None:
    memberships: list[Json] = read(brand, "/v1/me", brand.manager)["memberships"]

    assert [str(item["business_id"]) for item in memberships] == [brand.location_c]
    assert memberships[0]["brand_id"] == brand.brand_id
    assert memberships[0]["brand_name"] == "Mtsvane Ezo"
    assert memberships[0]["role"] == "staff"


def test_a_new_location_takes_settings_but_no_tokens_keys_webhooks_or_customers(
    brand: BrandWorld,
) -> None:
    world, client = brand.world, brand.world.workshop.client
    source = f"/v1/businesses/{world.business_b}"
    # The source has what must never travel: API keys, webhooks, customers.
    assert read(brand, f"{source}/api-keys", world.owner_b)["items"]
    assert read(brand, f"{source}/webhooks", world.owner_b)["items"]
    assert read(brand, f"{source}/contacts", world.owner_b)["items"]
    source_items = read(brand, f"{source}/knowledge?limit=100", world.owner_b)["items"]

    created = client.post(
        f"/v1/brands/{brand.brand_id}/locations/clone",
        json={
            "source_business_id": world.business_b,
            "name": "Mtsvane Ezo Saburtalo",
            "city": "Tbilisi",
        },
        headers=world.owner_b,
    )
    assert created.status_code == 201, created.text
    clone: Json = created.json()
    path = f"/v1/businesses/{clone['id']}"

    assert clone["brand_id"] == brand.brand_id
    assert clone["name"] == "Mtsvane Ezo Saburtalo"
    assert read(brand, f"{path}/api-keys", world.owner_b)["items"] == []
    assert read(brand, f"{path}/webhooks", world.owner_b)["items"] == []
    assert read(brand, f"{path}/contacts", world.owner_b)["items"] == []
    channels: list[Json] = read(brand, f"{path}/channels", world.owner_b)
    assert all(channel["status"] == "pending" for channel in channels)
    assert all(channel.get("account_id") is None for channel in channels)
    copied = read(brand, f"{path}/knowledge?limit=100", world.owner_b)["items"]
    copied_titles = {item["title"] for item in copied}
    assert copied_titles
    # Everything but menu-import drafts travels, under new ids.
    assert copied_titles <= {item["title"] for item in source_items}
    assert all(
        item["source"] == "menu_import"
        for item in source_items
        if item["title"] not in copied_titles
    )
    assert not {item["id"] for item in copied} & {item["id"] for item in source_items}
    # The brand's own team reaches the new location, and only through it.
    assert read(brand, path, brand.co_owner)["id"] == clone["id"]
    assert client.get(path, headers=brand.manager).status_code == 404


def test_a_location_override_replaces_the_shared_fact_there_only(
    brand: BrandWorld,
) -> None:
    world, client = brand.world, brand.world.workshop.client
    overridden = client.post(
        f"/v1/businesses/{brand.location_c}/knowledge/brand-overrides",
        json={"shared_key": "parking"},
        headers=world.owner_b,
    )
    assert overridden.status_code == 201, overridden.text
    assert overridden.json()["shared_key"] == "parking"

    shared: list[Json] = read(
        brand, f"/v1/brands/{brand.brand_id}/knowledge", world.owner_b
    )["items"]
    parking = next(item for item in shared if item["shared_key"] == "parking")
    assert parking["overridden_in"] == [brand.location_c]
    # A second override of the same fact in the same location is refused.
    again = client.post(
        f"/v1/businesses/{brand.location_c}/knowledge/brand-overrides",
        json={"shared_key": "parking"},
        headers=world.owner_b,
    )
    assert again.status_code == 409, again.text
