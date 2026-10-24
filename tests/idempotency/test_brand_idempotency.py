"""
Idempotency-Key on the brand operations that create something: a retried
"Create a brand" makes one brand and answers the first answer again, a
retried "New location from…" makes one location, and the same key with
another body is refused instead of making a second one.
"""

from typing import Any

from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE

type JsonObject = dict[str, Any]

BRAND_KEY: str = "7d2e9b14-3c5a-4f60-8e1b-2a9c4d6f8b03"
CLONE_KEY: str = "5a8c1e3f-9b2d-4c7e-a610-3f4b8d2e9c15"


def keyed(token: str, key: str) -> dict[str, str]:
    return {**bearer(token), "Idempotency-Key": key}


def first_business(workshop: Workshop, token: str) -> str:
    created = workshop.client.post(
        "/v1/assistants",
        json={"name": "Mtsvane Ezo Vera", "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return str(created.json()["business"]["id"])


def test_a_retried_brand_creation_makes_one_brand(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    body: JsonObject = {
        "name": "Mtsvane Ezo",
        "business_id": first_business(workshop, token),
    }

    first = workshop.client.post(
        "/v1/brands", json=body, headers=keyed(token, BRAND_KEY)
    )
    retry = workshop.client.post(
        "/v1/brands", json=body, headers=keyed(token, BRAND_KEY)
    )
    reused = workshop.client.post(
        "/v1/brands",
        json={**body, "name": "Another chain"},
        headers=keyed(token, BRAND_KEY),
    )

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json() == first.json()
    assert retry.headers["idempotent-replayed"] == "true"
    assert reused.status_code == 409
    assert reused.json()["reasons"][0]["code"] == "idempotency_key_reused"
    brands = workshop.client.get("/v1/brands", headers=bearer(token)).json()
    assert [brand["name"] for brand in brands] == ["Mtsvane Ezo"]


def test_a_retried_new_location_makes_one_location(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    source_id = first_business(workshop, token)
    created = workshop.client.post(
        "/v1/brands",
        json={"name": "Mtsvane Ezo", "business_id": source_id},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    clone = f"/v1/brands/{created.json()['id']}/locations/clone"
    body: JsonObject = {"source_business_id": source_id, "name": "Mtsvane Ezo Vake"}

    first = workshop.client.post(clone, json=body, headers=keyed(token, CLONE_KEY))
    retry = workshop.client.post(clone, json=body, headers=keyed(token, CLONE_KEY))

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json()["id"] == first.json()["id"]
    assert retry.headers["idempotent-replayed"] == "true"
    brand = workshop.client.get(
        f"/v1/brands/{created.json()['id']}", headers=bearer(token)
    ).json()
    assert sorted(location["name"] for location in brand["locations"]) == [
        "Mtsvane Ezo Vake",
        "Mtsvane Ezo Vera",
    ]
