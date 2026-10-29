"""
The owner's checks among the changes not live yet: a check written or
edited after the live version was last checked waits in `owner_checks`
until an "Apply changes" asks it (or "Check now" passed on the live
version), and never makes the sheet say everything is live.
"""

from tests.assistants.update_steps import (
    PERSON_QUESTION,
    add_check,
    apply_and_settle,
    check_now,
    dog_check,
    edit_check,
    launched,
)
from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import read_pending


def test_a_new_check_waits_until_an_apply_asks_it(workshop: Workshop) -> None:
    assistant = launched(workshop)
    assert read_pending(workshop, assistant)["count"] == 0

    check = add_check(
        workshop,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    pending = read_pending(workshop, assistant)

    assert pending["has_unapplied_changes"] is True
    assert pending["count"] == 1
    assert pending["changes"] == []
    assert pending["owner_checks"] == [
        {
            "autotest_case_id": check["id"],
            "action": "added",
            "question": PERSON_QUESTION,
            "expectation": "must_hand_off",
            "expected_text": None,
            "language": "ru",
        }
    ]

    applied = apply_and_settle(workshop, assistant)

    assert applied["stage"] == "live", applied
    assert applied["version_number"] == 2
    assert read_pending(workshop, assistant)["count"] == 0


def test_an_edited_check_waits_again_and_a_paused_one_does_not(
    workshop: Workshop,
) -> None:
    assistant = launched(workshop)
    check = add_check(
        workshop,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    assert apply_and_settle(workshop, assistant)["stage"] == "live"

    edit_check(workshop, assistant, str(check["id"]), {"question": "Позовите человека"})
    edited = read_pending(workshop, assistant)["owner_checks"]
    edit_check(workshop, assistant, str(check["id"]), {"is_active": False})
    paused = read_pending(workshop, assistant)

    assert [(item["action"], item["question"]) for item in edited] == [
        ("changed", "Позовите человека")
    ]
    assert paused["owner_checks"] == []
    assert paused["count"] == 0


def test_a_passed_check_now_counts_as_checked_and_a_failed_one_does_not(
    workshop: Workshop,
) -> None:
    assistant = launched(workshop)
    person = add_check(
        workshop,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    dog = dog_check(workshop, assistant)

    passed = check_now(workshop, assistant, str(person["id"]))
    failed = check_now(workshop, assistant, str(dog["id"]))
    pending = read_pending(workshop, assistant)

    assert passed.status_code == 200, passed.text
    assert passed.json()["outcome"] == "passed"
    assert failed.json()["outcome"] == "failed"
    assert [item["autotest_case_id"] for item in pending["owner_checks"]] == [dog["id"]]
    assert pending["count"] == 1


def test_a_check_that_changed_after_check_now_waits_again(
    workshop: Workshop,
) -> None:
    assistant = launched(workshop)
    person = add_check(
        workshop,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    assert check_now(workshop, assistant, str(person["id"])).status_code == 200
    assert read_pending(workshop, assistant)["count"] == 0

    edit_check(workshop, assistant, str(person["id"]), {"question": "Нужен человек"})

    assert read_pending(workshop, assistant)["owner_checks"][0]["action"] == "added"
