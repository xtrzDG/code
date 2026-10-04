"""The teaching routes over the real API: rating reasons, the Overview, checks."""

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import invite_staff
from tests.teaching.teaching_steps import (
    CAKE_QUESTION,
    ask,
    list_checks,
    live_assistant,
    save_check,
)


def test_a_bad_rating_with_its_reason_waits_in_the_overview(
    workshop: Workshop,
) -> None:
    assistant = live_assistant(workshop)
    answer = ask(workshop, assistant, CAKE_QUESTION)
    base = assistant.base

    rated = workshop.client.put(
        f"{base}/conversations/{answer.conversation_id}/rating",
        json={"rating": "bad", "reason": "wrong_info"},
        headers=assistant.headers,
    )
    wrong = workshop.client.put(
        f"{base}/conversations/{answer.conversation_id}/rating",
        json={"rating": "good", "reason": "tone"},
        headers=assistant.headers,
    )
    overview = workshop.client.get(
        f"{base}/answers-to-improve", params={"limit": 3}, headers=assistant.headers
    )

    assert rated.status_code == 200, rated.text
    assert rated.json()["rating_reason"] == "wrong_info"
    assert rated.json()["rated_message_id"] == answer.message_id
    assert wrong.status_code == 422
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["bad_rating_count"] == 1
    assert body["items"][0]["kind"] == "bad_rating"
    assert body["items"][0]["message_id"] == answer.message_id
    assert body["items"][0]["customer_message"] == CAKE_QUESTION
    too_many = workshop.client.get(
        f"{base}/answers-to-improve", params={"limit": 50}, headers=assistant.headers
    )
    assert too_many.status_code == 422


def test_checks_are_changed_removed_and_kept_by_owners(workshop: Workshop) -> None:
    assistant = live_assistant(workshop)
    staff = invite_staff(workshop, assistant)
    base = f"{assistant.base}/autotest-cases"
    check = save_check(
        workshop,
        assistant,
        {"question": CAKE_QUESTION, "expectation": "must_hand_off", "language": "ru"},
    )

    changed = workshop.client.patch(
        f"{base}/{check['id']}",
        json={
            "is_active": False,
            "expectation": "must_mention",
            "expected_text": "торт",
        },
        headers=assistant.headers,
    )
    missing_text = workshop.client.post(
        base,
        json={"question": "Есть парковка?", "expectation": "must_mention"},
        headers=assistant.headers,
    )
    duplicate = workshop.client.post(
        base,
        json={
            "question": CAKE_QUESTION,
            "expectation": "must_mention",
            "expected_text": "ТОРТ",
        },
        headers=assistant.headers,
    )
    by_staff = workshop.client.get(base, headers=staff)

    assert changed.status_code == 200, changed.text
    assert changed.json()["is_active"] is False
    assert changed.json()["expected_text"] == "торт"
    assert missing_text.status_code == 422
    assert duplicate.status_code == 409
    assert by_staff.status_code == 403
    removed = workshop.client.delete(f"{base}/{check['id']}", headers=assistant.headers)
    assert removed.status_code == 204
    assert list_checks(workshop, assistant) == []
    again = workshop.client.delete(f"{base}/{check['id']}", headers=assistant.headers)
    assert again.status_code == 404
