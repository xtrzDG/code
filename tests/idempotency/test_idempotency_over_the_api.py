"""
Idempotency-Key on the real application: a retried "Create an AI
assistant" makes one business and answers the first answer again, the same
key with another body is refused, a retried staff reply stores one message,
and the five creating operations document the header.
"""

from typing import Any, cast

from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, WIDGET_SESSION, open_restaurant
from tests.e2e.widget_turns import ask_widget

type JsonObject = dict[str, Any]

KEY: str = "0c6f3a4e-2b1d-4e8f-9a7c-5d3b2e1f0a9c"
IDEMPOTENT_OPERATIONS: set[str] = {
    "POST /v1/assistants",
    "POST /v1/businesses/{business_id}/bookings",
    "POST /v1/businesses/{business_id}/conversations/{conversation_id}/messages",
    "POST /v1/businesses/{business_id}/billing/checkout",
    "POST /v1/businesses/{business_id}/billing/subscribe",
    "POST /v1/public-api/bookings",
    "POST /v1/public-api/leads",
    "POST /v1/public-api/webhooks",
}


def keyed(token: str, key: str = KEY) -> dict[str, str]:
    return {**bearer(token), "Idempotency-Key": key}


def test_a_retried_create_assistant_makes_one_business(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    body: JsonObject = {"name": "Salobie Bia", "niche_key": "restaurant"}

    first = workshop.client.post("/v1/assistants", json=body, headers=keyed(token))
    retry = workshop.client.post("/v1/assistants", json=body, headers=keyed(token))
    reused = workshop.client.post(
        "/v1/assistants",
        json={"name": "Cafe Leila", "niche_key": "cafe"},
        headers=keyed(token),
    )

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json() == first.json()
    assert retry.headers["idempotent-replayed"] == "true"
    listed = workshop.client.get("/v1/businesses", headers=bearer(token)).json()
    assert [business["name"] for business in listed] == ["Salobie Bia"]
    assert reused.status_code == 409
    assert reused.json()["reasons"][0]["code"] == "idempotency_key_reused"


def test_a_retried_staff_reply_stores_one_message(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)
    workshop.client.put(
        f"{restaurant.base}/channels/web", json={}, headers=restaurant.headers
    )
    handed_off = ask_widget(
        workshop,
        restaurant.business_id,
        WIDGET_SESSION,
        "Позовите, пожалуйста, менеджера",
    )
    messages = f"{restaurant.base}/conversations/{handed_off['conversation_id']}"
    messages += "/messages"
    reply: JsonObject = {"text": "Здравствуйте, это Гиорги."}
    headers = {**restaurant.headers, "Idempotency-Key": KEY}

    sent = workshop.client.post(messages, json=reply, headers=headers)
    retried = workshop.client.post(messages, json=reply, headers=headers)

    assert (sent.status_code, retried.status_code) == (201, 201)
    assert retried.json()["message"]["id"] == sent.json()["message"]["id"]
    stored = workshop.client.get(messages, headers=restaurant.headers).json()
    staff_texts = [
        message["text"] for message in stored["items"] if message["author"] == "staff"
    ]
    assert staff_texts == ["Здравствуйте, это Гиорги."]


def test_the_creating_operations_document_the_key(workshop: Workshop) -> None:
    paths = cast(dict[str, JsonObject], workshop.application.openapi()["paths"])
    documented: set[str] = set()
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            names = {
                parameter["name"]
                for parameter in cast(list[JsonObject], operation.get("parameters", []))
                if parameter["in"] == "header"
            }
            if "Idempotency-Key" in names:
                documented.add(f"{method.upper()} {path}")

    assert documented == IDEMPOTENT_OPERATIONS
