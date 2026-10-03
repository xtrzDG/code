"""POST and GET .../knowledge/import-website over HTTP."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.http.website_import_routes import build_website_import_router
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.fakes import FakeUserAuthenticationOperator
from tests.knowledge.routes_fixture import OWNER, STAFF, STRANGER, operator
from tests.knowledge.website_import.website_import_world import WebsiteImportWorld


def build_client(world: WebsiteImportWorld) -> TestClient:
    current_user = build_current_user_dependency(
        FakeUserAuthenticationOperator(
            {
                "owner-token": world.owner_id,
                "staff-token": world.staff_id,
                "stranger-token": UserId(),
            }
        )
    )
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_website_import_router(
            start_website_import_operator=operator(world.start),
            get_website_import_operator=operator(world.get),
            current_user=current_user,
        )
    )
    return TestClient(application)


def test_an_import_is_started_followed_and_reviewed_over_http() -> None:
    world = WebsiteImportWorld()
    client = build_client(world)
    url = f"/v1/businesses/{world.business.id}/knowledge/import-website"

    assert client.get(f"{url}/current", headers=OWNER).json() == {"current": None}

    started = client.post(url, json={"url": "https://cafe.example"}, headers=STAFF)
    assert started.status_code == 202
    body: dict[str, Any] = started.json()
    assert body["status"] == "queued"
    assert body["id"].startswith("website_import_")

    world.run_queued()
    current: dict[str, Any] = client.get(f"{url}/current", headers=OWNER).json()[
        "current"
    ]
    assert current["id"] == body["id"]
    assert current["status"] == "done"
    assert current["pages_read"] == 5
    assert current["result"]["batch_id"].startswith("menu_import_")
    assert [row["item"]["title"] for row in current["result"]["items"]][:2] == [
        "Opening hours",
        "Adjarian khachapuri",
    ]


def test_refusals_carry_their_reason() -> None:
    world = WebsiteImportWorld()
    client = build_client(world)
    url = f"/v1/businesses/{world.business.id}/knowledge/import-website"

    private = client.post(url, json={"url": "http://192.168.0.1/admin"}, headers=OWNER)
    not_a_link = client.post(url, json={"url": "cafe"}, headers=OWNER)
    client.post(url, json={"url": "https://cafe.example"}, headers=OWNER)
    running = client.post(url, json={"url": "https://cafe.example"}, headers=OWNER)
    stranger = client.post(url, json={"url": "https://cafe.example"}, headers=STRANGER)

    assert private.status_code == 422
    assert private.json()["reasons"] == [
        {
            "code": "website_link_invalid",
            "message": "The address must be a public address.",
            "details": ["not_public"],
        }
    ]
    assert not_a_link.status_code == 422
    assert running.status_code == 409
    assert running.json()["reasons"][0]["code"] == "website_import_running"
    assert stranger.status_code == 404
