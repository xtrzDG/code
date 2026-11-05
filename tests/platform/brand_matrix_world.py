"""
The world of the brand authorization matrix, on top of the business
matrix's world (tests/platform/authorization_world.py): business B (the
demo restaurant) and C, a second location of B's owner, form a brand; a
regional manager runs C only; a second manager is the target of the team
routes; D is a business of B's owner outside the brand; the brand shares
one fact. Business A's owner and staff stay strangers to the brand.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, cast

from tests.e2e.harness import bearer
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.platform.authorization_world import (
    AuthorizationWorld,
    Headers,
    open_authorization_world,
)

type JsonObject = dict[str, Any]

MANAGER_PHONE: str = "+995 555 77 00 01"
SECOND_MANAGER_PHONE: str = "+995 555 77 00 02"
CO_OWNER_PHONE: str = "+995 555 77 00 03"
SHARED_KEY: str = "parking"


@dataclass
class BrandWorld:
    """The brand, its people and the ids its routes are called with."""

    world: AuthorizationWorld
    brand_id: str
    location_c: str
    outside_d: str
    manager: Headers
    manager_id: str
    co_owner: Headers
    path_values: dict[str, str] = field(default_factory=dict[str, str])


@contextmanager
def open_brand_world(
    environment: Mapping[str, str] = E2E_ENVIRONMENT,
) -> Generator[BrandWorld]:
    with open_authorization_world(environment) as world:
        yield build_brand_world(world)


def created(response: Any, status: int = 201) -> JsonObject:
    assert response.status_code == status, response.text
    return cast(JsonObject, response.json())


def build_brand_world(world: AuthorizationWorld) -> BrandWorld:
    client, owner = world.workshop.client, world.owner_b
    location_c = str(
        created(
            client.post(
                "/v1/businesses",
                json={"name": "Mtsvane Ezo Vake", "niche_key": "restaurant"},
                headers=owner,
            )
        )["id"]
    )
    outside_d = str(
        created(
            client.post(
                "/v1/businesses",
                json={"name": "Mtsvane Ezo Batumi", "niche_key": "restaurant"},
                headers=owner,
            )
        )["id"]
    )
    brand = created(
        client.post(
            "/v1/brands",
            json={"name": "Mtsvane Ezo", "business_id": world.business_b},
            headers=owner,
        )
    )
    brand_id = str(brand["id"])
    base = f"/v1/brands/{brand_id}"
    created(
        client.post(
            f"{base}/locations", json={"business_id": location_c}, headers=owner
        ),
        200,
    )
    for phone in (MANAGER_PHONE, SECOND_MANAGER_PHONE):
        created(
            client.post(
                f"{base}/members",
                json={
                    "phone_number": phone,
                    "role": "regional_manager",
                    "business_ids": [location_c],
                },
                headers=owner,
            )
        )
    team = created(
        client.post(
            f"{base}/members",
            json={"phone_number": CO_OWNER_PHONE, "role": "brand_owner"},
            headers=owner,
        )
    )["members"]
    created(
        client.post(
            f"{base}/knowledge",
            json={"kind": "faq", "title": "Parking", "shared_key": SHARED_KEY},
            headers=owner,
        )
    )
    workshop = world.workshop
    return BrandWorld(
        world=world,
        brand_id=brand_id,
        location_c=location_c,
        outside_d=outside_d,
        manager=bearer(workshop.sign_in_with_phone(MANAGER_PHONE)[0]),
        manager_id=member_id(team, "+995555770001"),
        co_owner=bearer(workshop.sign_in_with_phone(CO_OWNER_PHONE)[0]),
        path_values={
            "brand_id": brand_id,
            "business_id": location_c,
            "user_id": member_id(team, "+995555770002"),
            "shared_key": SHARED_KEY,
        },
    )


def member_id(team: list[JsonObject], phone_number: str) -> str:
    return next(
        str(member["user_id"])
        for member in team
        if member.get("phone_number") == phone_number
    )
