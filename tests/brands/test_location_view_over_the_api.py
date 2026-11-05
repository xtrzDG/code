"""
What a location sees of its brand over the API, on the brand matrix's
world (demo restaurant B, its further location C, a regional manager of C,
D outside the brand): plans priced as the location is billed, the brand's
shared facts with the location's own replacements, and the brand id in
/v1/me for a location's own owner who is not on the brand's team.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from tests.e2e.harness import bearer
from tests.platform.brand_matrix_world import BrandWorld, open_brand_world

type Json = dict[str, Any]

OUTSIDE_OWNER_PHONE: str = "+995 555 77 00 09"


@pytest.fixture(scope="module")
def brand() -> Iterator[BrandWorld]:
    with open_brand_world() as opened:
        yield opened


def read(brand: BrandWorld, path: str, headers: dict[str, str]) -> Any:
    response = brand.world.workshop.client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def chat(plans: Json) -> Json:
    return next(quote for quote in plans["quotes"] if quote["plan_key"] == "chat")


def test_a_further_location_is_quoted_the_price_it_is_billed(brand: BrandWorld) -> None:
    world, client = brand.world, brand.world.workshop.client
    first: Json = read(
        brand, f"/v1/businesses/{world.business_b}/billing/plans", world.owner_b
    )
    further: Json = read(
        brand, f"/v1/businesses/{brand.location_c}/billing/plans", world.owner_b
    )

    assert first["is_additional_location"] is False
    assert further["is_additional_location"] is True
    assert further["is_setup_fee_covered"] is True
    quoted = chat(further)
    assert quoted["monthly_price"] == chat(first)["additional_location_price"]
    assert quoted["setup_fee"]["money"]["amount_minor"] == 0
    trial = client.post(
        f"/v1/businesses/{brand.location_c}/billing/trial",
        json={"plan_key": "chat", "billing_period": "monthly"},
        headers=world.owner_b,
    )
    assert trial.status_code == 201, trial.text
    billed: Json = trial.json()["subscription"]["price"]["money"]
    shown: Json = (quoted["local_monthly_price"] or quoted["monthly_price"])["money"]
    assert billed == shown


def test_only_owners_see_the_location_plans(brand: BrandWorld) -> None:
    response = brand.world.workshop.client.get(
        f"/v1/businesses/{brand.location_c}/billing/plans", headers=brand.manager
    )

    assert response.status_code == 403, response.text


def test_a_location_sees_its_brands_answers_and_its_own_replacements(
    brand: BrandWorld,
) -> None:
    world, client = brand.world, brand.world.workshop.client
    path = f"/v1/businesses/{brand.location_c}/brand/knowledge"
    before: Json = read(brand, path, brand.manager)
    assert before["brand_id"] == brand.brand_id
    assert [item["own_item_id"] for item in before["items"]] == [None]

    created = client.post(
        f"/v1/businesses/{brand.location_c}/knowledge/brand-overrides",
        json={"shared_key": "parking"},
        headers=brand.manager,
    )
    assert created.status_code == 201, created.text

    after: Json = read(brand, path, brand.manager)
    assert [item["own_item_id"] for item in after["items"]] == [created.json()["id"]]
    outside: Json = read(
        brand, f"/v1/businesses/{brand.outside_d}/brand/knowledge", world.owner_b
    )
    assert outside == {"business_id": brand.outside_d, "brand_id": None, "items": []}


def test_a_locations_own_owner_off_the_brand_team_sees_its_brand_id(
    brand: BrandWorld,
) -> None:
    world, client = brand.world, brand.world.workshop.client
    invited = client.post(
        f"/v1/businesses/{brand.location_c}/members",
        json={"phone_number": OUTSIDE_OWNER_PHONE, "role": "owner"},
        headers=world.owner_b,
    )
    assert invited.status_code in (200, 201), invited.text
    headers = bearer(world.workshop.sign_in_with_phone(OUTSIDE_OWNER_PHONE)[0])

    memberships: list[Json] = read(brand, "/v1/me", headers)["memberships"]

    [membership] = memberships
    assert membership["business_id"] == brand.location_c
    assert membership["brand_id"] == brand.brand_id
    assert membership["brand_name"] is None
    assert membership["role"] == "owner"
