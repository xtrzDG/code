"""Knowledge routes: CRUD, search, tenant isolation and error status codes."""

from typing import Any

import pytest

from tests.knowledge.routes_fixture import OWNER, STAFF, STRANGER, RoutesFixture


def test_knowledge_crud_search_and_tenant_isolation(fixture: RoutesFixture) -> None:
    created = fixture.client.post(
        f"{fixture.base}/knowledge",
        json={
            "kind": "menu_item",
            "title": "Хачапури по-аджарски",
            "price_minor": 1800,
        },
        params={"language": "ka"},
        headers=STAFF,
    )
    item_id: str = created.json()["id"]
    listed = fixture.client.get(
        f"{fixture.base}/knowledge",
        params={"kind": "menu_item", "is_active": "true"},
        headers=OWNER,
    )
    patched = fixture.client.patch(
        f"{fixture.base}/knowledge/{item_id}",
        json={"body": "Сыр и яйцо", "is_active": True},
        headers=OWNER,
    )
    found = fixture.client.post(
        f"{fixture.base}/knowledge/search",
        json={"query": "аджарский хачапури", "language": "en", "limit": 3},
        headers=OWNER,
    )
    foreign_read = fixture.client.get(
        f"/v1/businesses/{fixture.other_business.id}/knowledge/{item_id}",
        headers=STRANGER,
    )
    deleted = fixture.client.delete(
        f"{fixture.base}/knowledge/{item_id}", headers=OWNER
    )
    missing = fixture.client.get(f"{fixture.base}/knowledge/{item_id}", headers=OWNER)

    assert created.status_code == 201
    assert created.json()["formatted_price"] == "18,00\xa0₾"
    assert created.json()["currency_code"] == "GEL"
    assert [item["id"] for item in listed.json()["items"]] == [item_id]
    assert listed.json()["next_cursor"] is None
    assert patched.status_code == 200
    assert patched.json()["body"] == "Сыр и яйцо"
    assert found.status_code == 200
    assert found.json()["items"][0]["id"] == item_id
    assert found.json()["items"][0]["formatted_price"] == "GEL18.00"
    assert foreign_read.status_code == 404
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert missing.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "status_code"),
    [
        (
            "post",
            "/knowledge",
            {"json": {"kind": "menu_item", "title": "X", "currency_code": "USD"}},
            422,
        ),
        ("post", "/knowledge", {"json": {"kind": "room_type", "title": "X"}}, 422),
        ("get", "/knowledge", {"params": {"kind": "spaceship"}}, 422),
        ("get", "/knowledge", {"params": {"is_active": "maybe"}}, 422),
        ("get", "/knowledge", {"params": {"limit": "0"}}, 422),
        ("get", "/knowledge", {"params": {"limit": "many"}}, 422),
        ("get", "/knowledge", {"params": {"cursor": "!!"}}, 422),
        ("get", "/knowledge/not-an-id", {}, 404),
        ("post", "/knowledge/search", {"json": {"query": "x", "limit": 50}}, 422),
    ],
)
def test_knowledge_errors_map_to_status_codes(
    fixture: RoutesFixture,
    method: str,
    path: str,
    kwargs: dict[str, Any],
    status_code: int,
) -> None:
    response = fixture.client.request(
        method,
        f"{fixture.base}{path}",
        headers=OWNER,
        **kwargs,
    )

    assert response.status_code == status_code, response.json()


def test_search_defaults_to_the_owner_language(fixture: RoutesFixture) -> None:
    fixture.client.post(
        f"{fixture.base}/knowledge",
        json={"kind": "menu_item", "title": "Pizza", "price_minor": 2550},
        headers=OWNER,
    )

    found = fixture.client.post(
        f"{fixture.base}/knowledge/search",
        json={"query": "pizza"},
        headers=OWNER,
    )

    assert found.json()["items"][0]["formatted_price"] == "25,50\xa0GEL"
