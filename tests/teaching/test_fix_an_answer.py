"""
"Fix this answer" over the real API: a live assistant's answer becomes a
knowledge item, the item a pending change, and the next "Apply changes"
puts it in front of customers; a check saved from it runs in that apply.
"""

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import apply_changes, read_apply
from tests.teaching.teaching_steps import (
    CAKE_ANSWER,
    CAKE_QUESTION,
    ask,
    autotest_results,
    correct,
    list_checks,
    live_assistant,
    pending_changes,
    save_check,
)


def test_a_corrected_answer_is_a_pending_change_until_it_is_applied(
    workshop: Workshop,
) -> None:
    assistant = live_assistant(workshop)
    answer = ask(workshop, assistant, CAKE_QUESTION)
    assert CAKE_ANSWER not in answer.text

    draft = workshop.client.get(answer.path(assistant), headers=assistant.headers)

    assert draft.status_code == 200, draft.text
    assert draft.json() == {
        "conversation_id": answer.conversation_id,
        "message_id": answer.message_id,
        "question": CAKE_QUESTION,
        "answer": answer.text,
        "language": "ru",
        "suggested_scope": "faq",
        "current_fact": None,
        "is_corrected": False,
        "guard_reasons": [],
    }

    result = correct(
        workshop,
        assistant,
        answer,
        {"scope": "faq", "question": CAKE_QUESTION, "correct_answer": CAKE_ANSWER},
    )

    assert result["is_new"] is True
    assert result["question"] == CAKE_QUESTION
    assert result["language"] == "ru"
    assert result["item"]["kind"] == "faq"
    assert result["item"]["title"] == CAKE_QUESTION
    assert result["item"]["body"] == CAKE_ANSWER
    assert {
        "area": "questions",
        "action": "added",
        "item_kind": "faq",
        "subject": CAKE_QUESTION,
    }.items() <= next(
        change
        for change in pending_changes(workshop, assistant)
        if change.get("subject") == CAKE_QUESTION
    ).items()
    again = workshop.client.get(answer.path(assistant), headers=assistant.headers)
    assert again.json()["is_corrected"] is True
    assert again.json()["current_fact"]["body"] == CAKE_ANSWER

    # Customers still get the live version until the owner applies.
    assert CAKE_ANSWER not in ask(workshop, assistant, CAKE_QUESTION).text
    started = apply_changes(workshop, assistant)
    assert started["stage"] == "checking"
    workshop.run_queued_jobs()
    assert read_apply(workshop, assistant)["stage"] == "live"
    assert pending_changes(workshop, assistant) == []

    later = ask(workshop, assistant, CAKE_QUESTION, "visitor_fedcba9876543210")
    assert CAKE_ANSWER in later.text


def test_correcting_the_same_answer_again_updates_its_item(
    workshop: Workshop,
) -> None:
    assistant = live_assistant(workshop)
    answer = ask(workshop, assistant, CAKE_QUESTION)
    first = correct(
        workshop,
        assistant,
        answer,
        {"scope": "faq", "question": CAKE_QUESTION, "correct_answer": CAKE_ANSWER},
    )

    second = correct(
        workshop,
        assistant,
        answer,
        {"scope": "faq", "correct_answer": "Да, можно, но только торт."},
    )

    assert second["is_new"] is False
    assert second["item"]["knowledge_item_id"] == first["item"]["knowledge_item_id"]
    assert second["item"]["body"] == "Да, можно, но только торт."
    knowledge = workshop.client.get(
        f"{assistant.base}/knowledge", headers=assistant.headers
    ).json()["items"]
    assert [item["title"] for item in knowledge].count(CAKE_QUESTION) == 1


def test_a_check_saved_from_a_correction_runs_in_the_next_quick_check(
    workshop: Workshop,
) -> None:
    assistant = live_assistant(workshop)
    answer = ask(workshop, assistant, CAKE_QUESTION)
    correct(
        workshop,
        assistant,
        answer,
        {"scope": "faq", "question": CAKE_QUESTION, "correct_answer": CAKE_ANSWER},
    )
    check = save_check(
        workshop,
        assistant,
        {
            "question": CAKE_QUESTION,
            "expectation": "must_mention",
            "expected_text": "своим тортом",
            "language": "ru",
            "source": "correction",
            "source_conversation_id": answer.conversation_id,
            "source_message_id": answer.message_id,
        },
    )
    assert check["last_result"] is None

    started = apply_changes(workshop, assistant)
    workshop.run_queued_jobs()

    assert read_apply(workshop, assistant)["stage"] == "live"
    owner_checks = [
        result
        for result in autotest_results(
            workshop, assistant, str(started["assistant_version_id"])
        )
        if result["kind"] == "owner_check"
    ]
    assert len(owner_checks) == 1
    assert owner_checks[0]["autotest_case_id"] == check["id"]
    assert owner_checks[0]["outcome"] == "passed"
    assert owner_checks[0]["scores"] == []
    assert owner_checks[0]["transcript"][0] == {
        "author": "customer",
        "text": CAKE_QUESTION,
    }
    listed = list_checks(workshop, assistant)
    assert listed[0]["id"] == check["id"]
    assert listed[0]["last_result"]["outcome"] == "passed"
