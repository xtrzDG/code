"""The website chat's "Talk to a person" against the whole API."""

from typing import Any

from tests.e2e.harness import Workshop
from tests.e2e.journeys import OpenRestaurant, open_restaurant
from tests.e2e.widget_turns import ask_widget

VISITOR: str = "visitor_handoff_0123456789"
OTHER_VISITOR: str = "visitor_handoff_9876543210"


def open_web_chat(workshop: Workshop) -> OpenRestaurant:
    restaurant = open_restaurant(workshop)
    web_chat = workshop.client.put(
        f"{restaurant.base}/channels/web", json={}, headers=restaurant.headers
    )
    assert web_chat.json()["status"] == "connected"
    return restaurant


def ask_for_person(
    workshop: Workshop, restaurant: OpenRestaurant, session_key: str = VISITOR
) -> Any:
    return workshop.client.post(
        f"/v1/widget/{restaurant.business_id}/handoff",
        json={"session_key": session_key, "language": "ru"},
        headers={"Origin": "https://salobie.example"},
    )


def handoffs(workshop: Workshop, restaurant: OpenRestaurant) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = workshop.client.get(
        f"{restaurant.base}/handoffs", headers=restaurant.headers
    ).json()["items"]
    return items


def test_a_visitor_who_has_not_written_reaches_a_person(workshop: Workshop) -> None:
    restaurant = open_web_chat(workshop)

    response = ask_for_person(workshop, restaurant)

    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == "*"
    body = response.json()
    assert body["is_handed_off"] is True
    assert body["language"] == "ru"
    assert body["direction"] == "ltr"
    assert body["text"].startswith("Ваш вопрос передан коллеге.")
    [handoff] = handoffs(workshop, restaurant)
    assert handoff["reason"] == "customer_request"
    assert handoff["conversation_id"] == body["conversation_id"]
    # The visitor's chat shows the promise once (polling skips it by id).
    polled = workshop.client.get(
        f"/v1/widget/{restaurant.business_id}/messages",
        headers={"X-Widget-Session-Key": VISITOR},
    ).json()
    assert polled["is_handed_off"] is True
    assert polled["cursor"] == body["message_id"]
    # Staff hear about it in their linked Telegram chat.
    workshop.run_queued_jobs()
    alerts = [
        message
        for message in workshop.telegram.bodies("sendMessage")
        if str(message.get("chat_id")) == "70001"
    ]
    assert alerts, workshop.telegram.paths()


def test_the_staff_summary_quotes_the_visitors_last_message(
    workshop: Workshop,
) -> None:
    restaurant = open_web_chat(workshop)
    asked = ask_widget(
        workshop, restaurant.business_id, VISITOR, "Есть ли у вас веганское меню?"
    )

    response = ask_for_person(workshop, restaurant)

    assert response.json()["conversation_id"] == asked["conversation_id"]
    [handoff] = handoffs(workshop, restaurant)
    assert "Есть ли у вас веганское меню?" in handoff["summary"]


def test_asking_again_notifies_nobody_twice(workshop: Workshop) -> None:
    restaurant = open_web_chat(workshop)
    first = ask_for_person(workshop, restaurant).json()

    again = ask_for_person(workshop, restaurant)

    assert again.status_code == 200
    assert again.json()["conversation_id"] == first["conversation_id"]
    assert again.json()["is_handed_off"] is True
    assert again.json()["text"] is None
    assert again.json()["message_id"] is None
    assert len(handoffs(workshop, restaurant)) == 1


def test_messages_after_the_request_wait_for_staff(workshop: Workshop) -> None:
    restaurant = open_web_chat(workshop)
    ask_for_person(workshop, restaurant)
    model_calls = workshop.model.assistant_calls

    reply = ask_widget(workshop, restaurant.business_id, VISITOR, "Я жду ответа")

    assert reply["is_handed_off"] is True
    assert reply["text"] is None
    assert workshop.model.assistant_calls == model_calls


def test_a_switched_off_chat_has_no_person_to_reach(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)

    response = ask_for_person(workshop, restaurant)

    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == "*"


def test_a_script_cannot_page_the_team_every_second(workshop: Workshop) -> None:
    restaurant = open_web_chat(workshop)
    statuses = [
        ask_for_person(workshop, restaurant, f"visitor_flood_{index:012d}").status_code
        for index in range(12)
    ]

    assert statuses[:10] == [200] * 10
    assert statuses[10:] == [429, 429]
    assert len(handoffs(workshop, restaurant)) == 10
