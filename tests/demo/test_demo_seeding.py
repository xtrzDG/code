"""
SEED_DEMO_DATA: the API fills a fresh instance with the demo businesses at
startup, once, without calling any provider; the dashboard and every list
of the cabinet have something to show.
"""

from typing import Any, cast

from fastapi.testclient import TestClient

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

type JsonObject = dict[str, Any]

DEMO_ENVIRONMENT: dict[str, str] = {**E2E_ENVIRONMENT, "SEED_DEMO_DATA": "true"}
DEMO_OWNER_EMAIL: str = "demo@example.com"
DEMO_OWNER_PHONE: str = "+995 555 00 00 01"
DEMO_STAFF_PHONE: str = "+995 555 00 00 02"
RESTAURANT: str = "Mtsvane Ezo"
SALON: str = "Studio Lindenblatt"
# Lists of a business and how many rows each shows at least.
RESTAURANT_LISTS: dict[str, int] = {
    "conversations?limit=100": 38,
    "bookings?limit=100": 20,
    "leads": 4,
    "handoffs": 4,
    "unanswered-questions": 5,
    "knowledge": 25,
    "resources": 4,
    "contacts": 38,
    "audit-log": 5,
}


def list_size(client: TestClient, path: str, headers: dict[str, str]) -> int:
    response = client.get(path, headers=headers)
    assert response.status_code == 200, (path, response.text)
    body: Any = response.json()
    if isinstance(body, list):
        return len(cast(list[JsonObject], body))

    return len(cast(list[JsonObject], cast(JsonObject, body)["items"]))


def businesses_by_name(
    client: TestClient, headers: dict[str, str]
) -> dict[str, JsonObject]:
    response = client.get("/v1/businesses", headers=headers)
    assert response.status_code == 200, response.text
    return {str(business["name"]): business for business in response.json()}


def sign_in_owner(workshop: Workshop) -> dict[str, str]:
    token, _ = workshop.sign_in_with_email(DEMO_OWNER_EMAIL)
    return bearer(token)


def test_the_demo_owner_gets_a_busy_restaurant_and_a_berlin_salon() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        businesses = businesses_by_name(client, headers)
        assert set(businesses) == {RESTAURANT, SALON}
        restaurant, salon = businesses[RESTAURANT], businesses[SALON]
        assert (restaurant["country_code"], restaurant["currency_code"]) == (
            "GE",
            "GEL",
        )
        assert (salon["country_code"], salon["currency_code"]) == ("DE", "EUR")
        assert salon["languages"] == ["de", "en"]
        base = f"/v1/businesses/{restaurant['id']}"
        dashboard: JsonObject = client.get(f"{base}/dashboard", headers=headers).json()
        for path, minimum in RESTAURANT_LISTS.items():
            assert list_size(client, f"{base}/{path}", headers) >= minimum, path

        versions: list[JsonObject] = client.get(
            f"{base}/assistant-versions", headers=headers
        ).json()
        published = next(v for v in versions if v["status"] == "published")
        readiness: JsonObject = client.get(
            f"{base}/assistant-versions/{published['id']}/go-live-readiness",
            headers=headers,
        ).json()
        run: JsonObject = client.get(
            f"{base}/assistant-versions/{published['id']}/autotest-run",
            headers=headers,
        ).json()
        channels: list[JsonObject] = client.get(
            f"{base}/channels", headers=headers
        ).json()
        billing: JsonObject = client.get(f"{base}/billing", headers=headers).json()
        salon_bookings = list_size(
            client, f"/v1/businesses/{salon['id']}/bookings?limit=100", headers
        )

    assert dashboard["conversation_count"] >= 35
    assert {row["language"] for row in dashboard["languages"]} == {
        "ka",
        "ru",
        "en",
        "he",
        "ar",
    }
    assert {row["status"] for row in dashboard["bookings_by_status"]} == {
        "confirmed",
        "completed",
        "no_show",
        "cancelled",
    }
    assert dashboard["lead_count"] >= 3
    assert dashboard["handoff_count"] >= 3
    assert dashboard["open_unanswered_question_count"] >= 3
    assert 75 <= dashboard["package"]["voice_usage_percent"] < 100
    assert sorted(v["status"] for v in versions) == ["archived", "draft", "published"]
    assert readiness["is_ready"] is True
    assert (run["status"], run["is_passed"], run["is_full_coverage"]) == (
        "finished",
        True,
        True,
    )
    assert {c["channel"] for c in channels if c["status"] == "connected"} >= {
        "telegram",
        "web_chat",
        "whatsapp",
        "phone",
    }
    assert billing["subscription"]["status"] == "trialing"
    assert salon_bookings >= 6


def test_a_conversation_card_shows_tool_calls_and_the_phone_call() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        restaurant = businesses_by_name(client, headers)[RESTAURANT]
        base = f"/v1/businesses/{restaurant['id']}"
        page: JsonObject = client.get(
            f"{base}/conversations?limit=100", headers=headers
        ).json()
        phone = next(c for c in page["items"] if c["channel"] == "phone")
        card: JsonObject = client.get(
            f"{base}/conversations/{phone['id']}", headers=headers
        ).json()
        rtl = [c for c in page["items"] if c["language"] in ("he", "ar")]

    assert card["calls"][0]["transcript"].startswith("[00:00] assistant:")
    assert card["calls"][0]["outcome"] == "booking"
    assert [
        call["tool_name"] for m in card["messages"] for call in m["tool_calls"]
    ] == ["check_availability", "create_booking", "search_knowledge"]
    assert card["bookings"][0]["status"] == "confirmed"
    assert len(rtl) == 4


def test_seeding_twice_keeps_one_demo_and_the_worker_calls_no_provider() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        restaurant = businesses_by_name(client, headers)[RESTAURANT]
        conversations = f"/v1/businesses/{restaurant['id']}/conversations?limit=100"
        first_count = list_size(client, conversations, headers)

    # A restart runs the startup again over the same storage (and sessions).
    with workshop.client as client:
        names = list(businesses_by_name(client, headers))
        second_count = list_size(client, conversations, headers)
        tick = workshop.container.gateways.background_worker().run_once()

    assert sorted(names) == [RESTAURANT, SALON]
    assert second_count == first_count
    assert int(tick.failures) == 0
    # Only the platform bot was set up at startup; no reminder, notification
    # or webhook went to the made-up channel credentials.
    assert all("platform-bot" in path for path in workshop.telegram.paths())
    assert workshop.meta.requests == []
    assert workshop.elevenlabs.requests == []


def test_the_staff_member_sees_only_the_restaurant() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        token, _ = workshop.sign_in_with_phone(DEMO_STAFF_PHONE)
        names = list(businesses_by_name(client, bearer(token)))
        workshop.clock.advance(60)
        owner_token, _ = workshop.sign_in_with_phone(DEMO_OWNER_PHONE)
        owner_names = list(businesses_by_name(client, bearer(owner_token)))

    assert names == [RESTAURANT]
    assert sorted(owner_names) == [RESTAURANT, SALON]


def test_without_the_setting_the_instance_stays_empty() -> None:
    workshop = start_workshop()
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        assert businesses_by_name(client, headers) == {}
