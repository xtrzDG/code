"""
"Check now": one of the owner's checks asked once of the version customers
talk to, through the scenario runner of the autotests, with the outcome
and why it failed in the owner's words; kept on the check while it is
asked the same way, at most 30 an hour per business.
"""

from collections.abc import Iterator

import pytest

from tests.assistants.update_steps import (
    DOG_QUESTION,
    DOG_WORDS,
    PERSON_QUESTION,
    add_check,
    check_now,
    dog_check,
    edit_check,
    launched,
    list_checks,
)
from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import start_rehearsal_workshop
from tests.setup.launch_steps import create_assistant, make_launch_ready


@pytest.fixture
def rehearsal() -> Iterator[Workshop]:
    workshop = start_rehearsal_workshop()
    with workshop.client:
        yield workshop


def test_a_passing_check_says_so_with_the_live_answer(rehearsal: Workshop) -> None:
    assistant = launched(rehearsal)
    check = add_check(
        rehearsal,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )

    checked = check_now(rehearsal, assistant, str(check["id"]))

    assert checked.status_code == 200, checked.text
    outcome = checked.json()
    assert outcome["autotest_case_id"] == check["id"]
    assert (outcome["question"], outcome["outcome"]) == (PERSON_QUESTION, "passed")
    assert outcome["reason"] is None and outcome["check_codes"] == []
    assert outcome["conversation_id"] and outcome["answer_message_id"]
    [listed] = list_checks(rehearsal, assistant)
    assert listed["last_probe"]["outcome"] == "passed"
    assert listed["last_probe"]["checked_at"] == outcome["checked_at"]


@pytest.mark.parametrize(
    ("language", "reason"),
    [
        ("ru", f"Ответ должен упомянуть «{DOG_WORDS}», а не упомянул."),
        ("en", f"The answer must mention “{DOG_WORDS}”, and it did not."),
    ],
)
def test_a_failing_check_says_why_in_the_owner_language(
    rehearsal: Workshop, language: str, reason: str
) -> None:
    assistant = launched(rehearsal)
    check = dog_check(rehearsal, assistant)

    checked = check_now(rehearsal, assistant, str(check["id"]), language)

    assert checked.status_code == 200, checked.text
    outcome = checked.json()
    assert (outcome["question"], outcome["outcome"]) == (DOG_QUESTION, "failed")
    assert outcome["check_codes"] == ["expected_text_missing"]
    assert outcome["reason"] == reason
    assert outcome["answer"]
    [listed] = list_checks(rehearsal, assistant, language)
    assert listed["last_probe"]["reason"] == reason


def test_asking_a_check_differently_forgets_its_check_now(
    rehearsal: Workshop,
) -> None:
    assistant = launched(rehearsal)
    check = dog_check(rehearsal, assistant)
    assert check_now(rehearsal, assistant, str(check["id"])).status_code == 200

    edit_check(rehearsal, assistant, str(check["id"]), {"is_active": False})
    paused = list_checks(rehearsal, assistant)[0]
    edit_check(rehearsal, assistant, str(check["id"]), {"expected_text": "собак"})
    edited = list_checks(rehearsal, assistant)[0]

    assert paused["is_active"] is False
    assert edited["last_probe"] is None


def test_a_paused_check_can_still_be_asked(rehearsal: Workshop) -> None:
    assistant = launched(rehearsal)
    check = add_check(
        rehearsal,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    edit_check(rehearsal, assistant, str(check["id"]), {"is_active": False})

    checked = check_now(rehearsal, assistant, str(check["id"]))

    assert checked.status_code == 200, checked.text
    assert checked.json()["outcome"] == "passed"


def test_check_now_needs_a_live_assistant_and_a_check_of_the_business(
    rehearsal: Workshop,
) -> None:
    before_launch = create_assistant(rehearsal)
    make_launch_ready(rehearsal, before_launch)
    early = add_check(
        rehearsal,
        before_launch,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    other = launched(rehearsal)

    not_live = check_now(rehearsal, before_launch, str(early["id"]))
    foreign = check_now(rehearsal, other, str(early["id"]))

    assert not_live.status_code == 409
    assert foreign.status_code == 404


def test_thirty_checks_an_hour_per_business(rehearsal: Workshop) -> None:
    assistant = launched(rehearsal)
    check = add_check(
        rehearsal,
        assistant,
        {"question": PERSON_QUESTION, "expectation": "must_hand_off"},
    )
    case_id = str(check["id"])

    statuses = [
        rehearsal.client.post(
            f"{assistant.base}/autotest-cases/{case_id}/check",
            headers=assistant.headers,
        ).status_code
        for _ in range(31)
    ]
    refused = rehearsal.client.post(
        f"{assistant.base}/autotest-cases/{case_id}/check", headers=assistant.headers
    )
    rehearsal.clock.advance(3600)
    next_hour = check_now(rehearsal, assistant, case_id)

    assert statuses[:30] == [200] * 30
    assert statuses[30] == 429
    assert refused.status_code == 429
    assert int(refused.headers["Retry-After"]) > 0
    assert next_hour.status_code == 200
