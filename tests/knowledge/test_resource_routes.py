"""Resource and schedule exception routes, and the OpenAPI request bodies."""

from tests.knowledge.routes_fixture import OWNER, STAFF, STRANGER, RoutesFixture


def test_resources_and_schedule_exceptions(fixture: RoutesFixture) -> None:
    created = fixture.client.post(
        f"{fixture.base}/resources",
        json={"name": "Table 4", "capacity": 4},
        headers=STAFF,
    )
    resource_id: str = created.json()["id"]
    duplicate = fixture.client.post(
        f"{fixture.base}/resources",
        json={"name": "table 4", "capacity": 2},
        headers=STAFF,
    )
    patched = fixture.client.patch(
        f"{fixture.base}/resources/{resource_id}",
        json={"is_active": False},
        headers=OWNER,
    )
    listed = fixture.client.get(
        f"{fixture.base}/resources",
        params={"is_active": "false"},
        headers=OWNER,
    )
    holiday = fixture.client.post(
        f"{fixture.base}/schedule-exceptions",
        json={"date": "2027-01-07", "note": "Christmas"},
        headers=STAFF,
    )
    special = fixture.client.post(
        f"{fixture.base}/schedule-exceptions",
        json={
            "resource_id": resource_id,
            "date": "2026-12-31",
            "is_closed_all_day": False,
            "special_hours": [{"weekday": 4, "opens_at": 720, "closes_at": 1440}],
        },
        headers=STAFF,
    )
    for_resource = fixture.client.get(
        f"{fixture.base}/schedule-exceptions",
        params={"resource_id": resource_id, "from_date": "2026-12-01"},
        headers=OWNER,
    )
    past = fixture.client.post(
        f"{fixture.base}/schedule-exceptions",
        json={"date": "2026-01-01"},
        headers=OWNER,
    )
    bad_filter = fixture.client.get(
        f"{fixture.base}/schedule-exceptions",
        params={"from_date": "01.12.2026"},
        headers=OWNER,
    )
    deleted = fixture.client.delete(
        f"{fixture.base}/schedule-exceptions/{holiday.json()['id']}",
        headers=OWNER,
    )
    foreign_patch = fixture.client.patch(
        f"/v1/businesses/{fixture.other_business.id}/resources/{resource_id}",
        json={"is_active": True},
        headers=STRANGER,
    )

    assert created.status_code == 201
    assert created.json()["kind"] == "table"
    assert duplicate.status_code == 409
    assert patched.json()["is_active"] is False
    assert [item["id"] for item in listed.json()["items"]] == [resource_id]
    assert holiday.status_code == 201
    assert holiday.json()["weekday"] == 4
    assert special.status_code == 201
    assert [item["date"] for item in for_resource.json()["items"]] == [
        "2026-12-31",
        "2027-01-07",
    ]
    assert past.status_code == 422
    assert bad_filter.status_code == 422
    assert deleted.status_code == 204
    assert foreign_patch.status_code == 404


def test_openapi_documents_json_request_bodies(fixture: RoutesFixture) -> None:
    schema = fixture.client.get("/openapi.json").json()

    knowledge_post = schema["paths"]["/v1/businesses/{business_id}/knowledge"]["post"]
    step_put = schema["paths"]["/v1/businesses/{business_id}/profile/steps/{step}"][
        "put"
    ]
    body_schema = knowledge_post["requestBody"]["content"]["application/json"]["schema"]

    assert body_schema["title"] == "KnowledgeItemInput"
    assert "$ref" not in str(body_schema)
    assert (
        len(step_put["requestBody"]["content"]["application/json"]["schema"]["oneOf"])
        == 6
    )
