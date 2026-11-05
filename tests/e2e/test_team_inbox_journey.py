"""End to end over HTTP: the team inbox of a published restaurant. A website
visitor asks for a person; the owner leaves an internal note, takes the
conversation (a stale assignment is refused), fills a saved reply. The
note never reaches the language model, the visitor or a staff alert.
"""

from tests.e2e.harness import Workshop
from tests.e2e.journeys import WIDGET_SESSION, JsonObject, open_restaurant
from tests.e2e.widget_turns import ask_widget

NOTE_TEXT: str = "Постоянный гость, код скидки VIP-7731, не звонить после 21:00"
NOTE_MARKER: str = "VIP-7731"


def test_the_team_shares_a_handed_off_conversation_and_notes_stay_internal(
    workshop: Workshop,
) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    base, headers = restaurant.base, restaurant.headers
    client.put(f"{base}/channels/web", json={}, headers=headers)
    widget_messages = f"/v1/widget/{restaurant.business_id}/messages"

    # A visitor says hello; the owner notes something about them.
    greeted: JsonObject = ask_widget(
        workshop, restaurant.business_id, WIDGET_SESSION, "Здравствуйте, у меня вопрос"
    )
    conversation_id = str(greeted["conversation_id"])
    conversation_path = f"{base}/conversations/{conversation_id}"
    noted = client.post(
        f"{conversation_path}/notes", json={"text": NOTE_TEXT}, headers=headers
    )
    assert noted.status_code == 201, noted.text
    assert noted.json()["can_delete"] is True
    model_requests_before = len(workshop.llm.requests)

    # The visitor goes on and asks for a manager: the model answers twice
    # and never sees the note; neither the visitor nor the staff alert does.
    for text in ("Сколько стоит хачапури?", "Позовите менеджера, пожалуйста"):
        answered = ask_widget(workshop, restaurant.business_id, WIDGET_SESSION, text)
        assert NOTE_MARKER not in str(answered)
    assert answered["is_handed_off"] is True
    new_requests = workshop.llm.requests[model_requests_before:]
    assert new_requests
    assert all(NOTE_MARKER not in request.model_dump_json() for request in new_requests)
    polled = client.get(
        widget_messages, headers={"X-Widget-Session-Key": WIDGET_SESSION}
    )
    assert NOTE_MARKER not in polled.text
    assert all(NOTE_MARKER not in str(body) for body in workshop.telegram.bodies(""))
    card = client.get(conversation_path, headers=headers)
    assert NOTE_MARKER not in card.text
    assert card.json()["assignment"] == {
        "conversation_id": conversation_id,
        "assignee_user_id": None,
        "assigned_by": None,
        "assigned_at": None,
        "is_assigned_automatically": False,
        "assignment_revision": 0,
    }

    # The inbox shows the conversation as needing a person, nobody assigned.
    needs_person: JsonObject = client.get(
        f"{base}/inbox", params={"view": "needs_person"}, headers=headers
    ).json()
    assert [item["id"] for item in needs_person["items"]] == [conversation_id]
    row: JsonObject = needs_person["items"][0]
    assert (row["assignee_user_id"], row["note_count"]) == (None, 1)
    assert row["handoff"]["reason"] == "customer_request"
    assert NOTE_MARKER not in str(needs_person)
    assert needs_person["counts"] == {
        "needs_person": 1,
        "requests": 0,
        "mine": 0,
        "unassigned": 1,
    }

    # The owner takes it; a second click with the same revision is refused.
    revision = row["assignment_revision"]
    taken = client.post(
        f"{conversation_path}/assign",
        json={"assignee_user_id": restaurant.owner_id, "expected_revision": revision},
        headers=headers,
    )
    assert taken.status_code == 200, taken.text
    assert taken.json()["assignment_revision"] == revision + 1
    stale = client.post(
        f"{conversation_path}/assign",
        json={"assignee_user_id": None, "expected_revision": revision},
        headers=headers,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["reasons"][0]["code"] == "assignment_changed"
    # The card names the assignee and the revision the next change must name.
    assigned = client.get(conversation_path, headers=headers).json()["assignment"]
    assert (assigned["assignee_user_id"], assigned["assigned_by"]) == (
        restaurant.owner_id,
        restaurant.owner_id,
    )
    assert assigned["assignment_revision"] == revision + 1
    mine: JsonObject = client.get(
        f"{base}/inbox", params={"view": "mine"}, headers=headers
    ).json()
    assert [item["id"] for item in mine["items"]] == [conversation_id]
    assert (mine["counts"]["mine"], mine["counts"]["unassigned"]) == (1, 0)
    unknown_view = client.get(
        f"{base}/inbox", params={"view": "everything"}, headers=headers
    )
    assert unknown_view.status_code == 422

    # A saved reply in Russian and English: the Russian one, filled in.
    saved = client.post(
        f"{base}/quick-replies",
        json={
            "shortcut": "welcome",
            "title": "Приветствие",
            "variants": [
                {"language": "en", "text": "Hello from {business_name}!"},
                {"language": "ru", "text": "Здравствуйте! Это {business_name}."},
            ],
        },
        headers=headers,
    )
    assert saved.status_code == 201, saved.text
    filled: JsonObject = client.get(
        f"{conversation_path}/quick-replies", headers=headers
    ).json()
    assert [(item["language"], item["text"]) for item in filled["items"]] == [
        ("ru", "Здравствуйте! Это Salobie Bia.")
    ]

    # Deleting the note leaves nothing behind; the inbox reads are audited.
    deleted = client.delete(
        f"{conversation_path}/notes/{noted.json()['id']}", headers=headers
    )
    assert deleted.status_code == 204
    notes = client.get(f"{conversation_path}/notes", headers=headers).json()
    assert notes["items"] == []
    audit: JsonObject = client.get(f"{base}/audit-log", headers=headers).json()
    entities = {(entry["entity"], entry["action"]) for entry in audit["items"]}
    assert {
        ("inbox", "view"),
        ("conversation_note", "create"),
        ("conversation_note", "delete"),
        ("conversation_assignment", "update"),
        ("quick_reply", "create"),
    } <= entities
    assert NOTE_MARKER not in str(audit)
