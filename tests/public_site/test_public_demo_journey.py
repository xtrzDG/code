"""
The landing page's sandbox demos over the real container: the seeded demo
businesses chat with visitors without a token, every turn is a sandbox
turn (no real booking, no request in the owner's lists), only demo
businesses answer, and a visitor's conversation has a message budget.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

type JsonObject = dict[str, Any]

DEMO_ENVIRONMENT: dict[str, str] = {**E2E_ENVIRONMENT, "SEED_DEMO_DATA": "true"}
DEMO_OWNER_EMAIL: str = "demo@example.com"
RESTAURANT: str = "Mtsvane Ezo"
SALON: str = "Studio Lindenblatt"
SESSION_KEY: str = "visitor-session-0001"
UNKNOWN_BUSINESS_ID: str = "business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10"


def list_demos(client: TestClient, language: str = "en") -> JsonObject:
    response = client.get("/v1/public-demos", params={"language": language})
    assert response.status_code == 200, response.text
    return response.json()


def demo_by_name(client: TestClient) -> dict[str, JsonObject]:
    return {demo["business_name"]: demo for demo in list_demos(client)["demos"]}


def send(
    client: TestClient, business_id: str, text: str, session_key: str = SESSION_KEY
) -> Any:
    return client.post(
        f"/v1/public-demos/{business_id}/messages",
        json={"text": text, "session_key": session_key},
    )


def owner_list_size(
    workshop: Workshop, headers: dict[str, str], business_id: str, path: str
) -> int:
    response = workshop.client.get(
        f"/v1/businesses/{business_id}/{path}", headers=headers
    )
    assert response.status_code == 200, response.text
    return len(response.json()["items"])


def test_visitors_see_the_seeded_demos_in_their_language() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        english = list_demos(client)
        russian = list_demos(client, "ru")

    assert english["messages_per_hour"] == 20
    by_name = {demo["business_name"]: demo for demo in english["demos"]}
    assert set(by_name) == {RESTAURANT, SALON}
    restaurant = by_name[RESTAURANT]
    assert restaurant["niche_key"] == "restaurant"
    assert restaurant["niche_name"] == "Restaurants and cafes"
    assert restaurant["country_code"] == "GE"
    assert set(restaurant["languages"]) >= {"ka", "ru", "en"}
    assert restaurant["starters"] != []
    assert "owner" not in restaurant and "phone" not in str(restaurant).lower()
    russian_restaurant = next(
        demo for demo in russian["demos"] if demo["business_name"] == RESTAURANT
    )
    assert russian_restaurant["niche_name"] == "Рестораны и кафе"


def test_a_demo_booking_is_a_sandbox_record_the_owner_never_sees() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        restaurant_id = demo_by_name(client)[RESTAURANT]["business_id"]
        owner = bearer(workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])
        bookings_before = owner_list_size(
            workshop, owner, restaurant_id, "bookings?limit=100"
        )
        handoffs_before = owner_list_size(workshop, owner, restaurant_id, "handoffs")

        booked = send(client, restaurant_id, "Hello, I would like to book a table")
        handed_off = send(client, restaurant_id, "Can I talk to a manager?")

        assert booked.status_code == 200, booked.text
        reply = booked.json()
        assert reply["is_booking_made"] is True
        assert reply["text"]
        assert reply["language"] == "en"
        assert reply["messages_left"] == 19
        assert handed_off.status_code == 200, handed_off.text
        assert handed_off.json()["is_handoff_made"] is True
        assert handed_off.json()["messages_left"] == 18
        assert (
            owner_list_size(workshop, owner, restaurant_id, "bookings?limit=100")
            == bookings_before
        )
        assert (
            owner_list_size(workshop, owner, restaurant_id, "handoffs")
            == handoffs_before
        )


def test_only_demo_businesses_answer() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        unknown = send(client, UNKNOWN_BUSINESS_ID, "Hello")
        malformed = send(client, "not-a-business", "Hello")
        restaurant_id = demo_by_name(client)[RESTAURANT]["business_id"]
        empty = send(client, restaurant_id, "   ")
        bad_key = send(client, restaurant_id, "Hello", session_key="short")
        too_long = send(client, restaurant_id, "x" * 501)

    assert unknown.status_code == 404
    assert unknown.json()["error"] == "not_found"
    assert malformed.status_code in {404, 422}
    assert empty.status_code == 422
    assert bad_key.status_code == 422
    assert too_long.status_code == 422


def test_one_visitor_conversation_has_a_budget_per_hour() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        salon_id = demo_by_name(client)[SALON]["business_id"]
        answers = [send(client, salon_id, f"Question {index}") for index in range(20)]
        refused = send(client, salon_id, "One more question")
        other_visitor = send(
            client, salon_id, "Hello", session_key="another-visitor-0002"
        )

    assert [answer.status_code for answer in answers] == [200] * 20
    assert answers[-1].json()["messages_left"] == 0
    assert refused.status_code == 429
    assert int(refused.headers["retry-after"]) > 0
    assert other_visitor.status_code == 200


def test_configured_demos_replace_the_seeded_ones() -> None:
    seeded = start_workshop(DEMO_ENVIRONMENT)
    with seeded.client as client:
        salon_id = demo_by_name(client)[SALON]["business_id"]

    configured = start_workshop(
        {**DEMO_ENVIRONMENT, "PUBLIC_DEMO_BUSINESS_IDS": UNKNOWN_BUSINESS_ID}
    )
    with configured.client as client:
        demos = list_demos(client)["demos"]
        # Seeding creates new ids in a fresh instance: the configured id
        # names no business, so no demo can answer and none is offered.
        refused = send(client, salon_id, "Hello")

    assert demos == []
    assert refused.status_code == 404
