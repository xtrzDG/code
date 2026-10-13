"""
A brand's team acts in its locations with the role the brand gives it,
everywhere the cabinet asks, on the brand matrix's world (demo restaurant
B and its second location C; a regional manager of C; a co-owner of the
brand who is no member of either location's own team).
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


def test_editing_a_locations_own_answer_keeps_it_replacing_the_brands(
    brand: BrandWorld,
) -> None:
    world, client = brand.world, brand.world.workshop.client
    location = f"/v1/businesses/{brand.location_c}"
    created = client.post(
        f"{location}/knowledge/brand-overrides",
        json={"shared_key": "parking"},
        headers=world.owner_b,
    )
    assert created.status_code == 201, created.text

    edited = client.patch(
        f"{location}/knowledge/{created.json()['id']}",
        json={"body": "Free parking behind the Vake location.", "is_active": True},
        headers=world.owner_b,
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["shared_key"] == "parking"
    shared: list[Json] = read(
        brand, f"/v1/brands/{brand.brand_id}/knowledge", world.owner_b
    )["items"]
    parking = next(item for item in shared if item["shared_key"] == "parking")
    assert parking["overridden_in"] == [brand.location_c]


def test_the_brand_team_is_never_shown_as_platform_support(brand: BrandWorld) -> None:
    for headers, business_id in (
        (brand.manager, brand.location_c),
        (brand.co_owner, brand.world.business_b),
    ):
        view: Json = read(
            brand, f"/v1/businesses/{business_id}/support-access", headers
        )

        assert view["is_support_viewer"] is False
        assert view["viewer_can_write"] is False


def test_a_brand_owner_decides_about_support_access_a_manager_does_not(
    brand: BrandWorld,
) -> None:
    client = brand.world.workshop.client

    by_co_owner = client.delete(
        f"/v1/businesses/{brand.world.business_b}/support-access",
        headers=brand.co_owner,
    )
    by_manager = client.delete(
        f"/v1/businesses/{brand.location_c}/support-access", headers=brand.manager
    )

    assert by_co_owner.status_code == 204, by_co_owner.text
    assert by_manager.status_code == 403, by_manager.text


def test_the_inbox_offers_the_brand_team_as_assignees(brand: BrandWorld) -> None:
    assignees: list[Json] = read(
        brand, f"/v1/businesses/{brand.location_c}/inbox/assignees", brand.manager
    )["items"]
    roles = {str(item["user_id"]): item["role"] for item in assignees}

    assert roles[brand.manager_id] == "staff"
    co_owner_id = str(read(brand, "/v1/me", brand.co_owner)["user"]["id"])
    assert roles[co_owner_id] == "owner"


def test_a_change_answers_with_the_role_the_viewer_acts_with(
    brand: BrandWorld,
) -> None:
    client = brand.world.workshop.client
    path = f"/v1/businesses/{brand.world.business_b}"
    current: Json = read(brand, path, brand.co_owner)

    changed = client.patch(
        path,
        json={"name": current["name"], "expected_revision": current["revision"]},
        headers=brand.co_owner,
    )

    assert changed.status_code == 200, changed.text
    assert current["viewer_role"] == "owner"
    assert changed.json()["viewer_role"] == "owner"
