"""
An update that fails one of the owner's checks names it: the apply's
attention lists the check with its question, why it failed in the owner's
language and the test answer to fix, the version's results keep what the
check asked, and fixing that answer takes the check live with the next
"Apply changes".
"""

from typing import cast

import pytest

from tests.assistants.update_steps import (
    DOG_ANSWER,
    DOG_QUESTION,
    DOG_WORDS,
    JsonObject,
    apply_and_settle,
    dog_check,
    failed_checks,
    launched,
    list_checks,
)
from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import read_pending
from tests.setup.launch_steps import read_apply

REASONS: dict[str, str] = {
    "ru": f"Ответ должен упомянуть «{DOG_WORDS}», а не упомянул.",
    "en": f"The answer must mention “{DOG_WORDS}”, and it did not.",
    "ka": f"პასუხში უნდა ყოფილიყო „{DOG_WORDS}“, მაგრამ არ იყო.",
}


@pytest.mark.parametrize("language", ["ru", "en", "ka"])
def test_a_failed_check_is_named_with_its_question_and_why(
    workshop: Workshop, language: str
) -> None:
    assistant = launched(workshop)
    check = dog_check(workshop, assistant)

    applied = apply_and_settle(workshop, assistant, language)

    assert applied["stage"] == "needs_attention", applied
    [failed] = failed_checks(applied)
    assert failed["autotest_case_id"] == check["id"]
    assert (failed["question"], failed["expectation"], failed["expected_text"]) == (
        DOG_QUESTION,
        "must_mention",
        DOG_WORDS,
    )
    assert failed["outcome"] == "failed"
    assert failed["check_codes"] == ["expected_text_missing"]
    assert failed["reason"] == REASONS[language]
    assert failed["answer"]
    assert failed["conversation_id"] and failed["answer_message_id"]
    assert failed["assistant_version_id"] == applied["assistant_version_id"]


def test_the_failed_update_stays_a_draft_and_its_results_keep_the_check(
    workshop: Workshop,
) -> None:
    assistant = launched(workshop)
    check = dog_check(workshop, assistant)
    applied = apply_and_settle(workshop, assistant)

    run = workshop.client.get(
        f"{assistant.base}/assistant-versions/"
        f"{applied['assistant_version_id']}/autotest-run",
        headers=assistant.headers,
    )
    pending = read_pending(workshop, assistant)

    assert run.status_code == 200, run.text
    [result] = [
        result
        for result in cast(list[JsonObject], run.json()["results"])
        if result["kind"] == "owner_check"
    ]
    assert result["autotest_case_id"] == check["id"]
    assert result["owner_check"] == {
        "question": DOG_QUESTION,
        "expectation": "must_mention",
        "expected_text": DOG_WORDS,
    }
    assert result["conversation_id"] and result["answer_message_id"]
    # Customers still talk to the first version: the check is still pending.
    assert [item["autotest_case_id"] for item in pending["owner_checks"]] == [
        check["id"]
    ]
    assert [
        (draft["assistant_version_id"], draft["status"]) for draft in pending["drafts"]
    ] == [(applied["assistant_version_id"], "tests_failed")]


def test_fixing_the_named_answer_takes_the_check_live(workshop: Workshop) -> None:
    assistant = launched(workshop)
    check = dog_check(workshop, assistant)
    [failed] = failed_checks(apply_and_settle(workshop, assistant))

    corrected = workshop.client.post(
        f"{assistant.base}/conversations/{failed['conversation_id']}"
        f"/messages/{failed['answer_message_id']}/correction",
        json={"scope": "faq", "question": DOG_QUESTION, "correct_answer": DOG_ANSWER},
        headers=assistant.headers,
    )
    workshop.clock.advance(60)
    pending = read_pending(workshop, assistant)
    applied = apply_and_settle(workshop, assistant)

    assert corrected.status_code == 200, corrected.text
    assert [change["area"] for change in pending["changes"]] == ["questions"]
    assert pending["count"] == 2
    assert applied["stage"] == "live", applied
    assert applied["version_number"] == 3
    [listed] = [item for item in list_checks(workshop, assistant)]
    assert listed["id"] == check["id"]
    assert listed["last_result"]["outcome"] == "passed"
    assert listed["last_result"]["conversation_id"]
    assert listed["last_result"]["answer_message_id"]
    assert DOG_WORDS in listed["last_result"]["answer"]
    after = read_pending(workshop, assistant)
    assert (after["count"], after["drafts"]) == (0, [])
    assert read_apply(workshop, assistant)["attention"] == []
