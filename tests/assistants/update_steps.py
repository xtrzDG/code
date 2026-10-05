"""
Steps of updating a live assistant over the real API on the rehearsal model
of LLM_PROVIDER=scripted: the owner's checks, "Check now", the changes not
live yet, drafts and "Apply changes".
"""

from typing import Any, cast

from httpx import Response

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import (
    NewAssistant,
    apply_changes,
    create_assistant,
    go_live,
    make_launch_ready,
    read_apply,
)

type JsonObject = dict[str, Any]

# The rehearsal assistant passes these to a colleague ("человек").
PERSON_QUESTION: str = "Можно поговорить с человеком?"
# ... and has no answer to this one until the owner teaches it.
DOG_QUESTION: str = "Можно прийти с собакой?"
DOG_WORDS: str = "с собакой можно"
DOG_ANSWER: str = "Да, с собакой можно: для неё есть место на веранде."


def launched(workshop: Workshop) -> NewAssistant:
    """A restaurant whose first version is live."""

    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    go_live(workshop, assistant)
    workshop.clock.advance(60)
    return assistant


def add_check(
    workshop: Workshop, assistant: NewAssistant, body: JsonObject
) -> JsonObject:
    saved = workshop.client.post(
        f"{assistant.base}/autotest-cases", json=body, headers=assistant.headers
    )
    assert saved.status_code == 201, saved.text
    workshop.clock.advance(60)
    return dict(saved.json())


def edit_check(
    workshop: Workshop, assistant: NewAssistant, case_id: str, body: JsonObject
) -> JsonObject:
    edited = workshop.client.patch(
        f"{assistant.base}/autotest-cases/{case_id}",
        json=body,
        headers=assistant.headers,
    )
    assert edited.status_code == 200, edited.text
    workshop.clock.advance(60)
    return dict(edited.json())


def dog_check(workshop: Workshop, assistant: NewAssistant) -> JsonObject:
    """A check the rehearsal assistant fails until the owner fixes its answer."""

    return add_check(
        workshop,
        assistant,
        {
            "question": DOG_QUESTION,
            "expectation": "must_mention",
            "expected_text": DOG_WORDS,
        },
    )


def check_now(
    workshop: Workshop,
    assistant: NewAssistant,
    case_id: str,
    language: str | None = None,
) -> Response:
    checked = workshop.client.post(
        f"{assistant.base}/autotest-cases/{case_id}/check",
        params={} if language is None else {"language": language},
        headers=assistant.headers,
    )
    workshop.clock.advance(60)
    return checked


def list_checks(
    workshop: Workshop, assistant: NewAssistant, language: str | None = None
) -> list[JsonObject]:
    listed = workshop.client.get(
        f"{assistant.base}/autotest-cases",
        params={} if language is None else {"language": language},
        headers=assistant.headers,
    )
    assert listed.status_code == 200, listed.text
    return cast(list[JsonObject], listed.json()["items"])


def apply_and_settle(
    workshop: Workshop, assistant: NewAssistant, language: str | None = None
) -> JsonObject:
    """Apply changes, let the worker play the quick check; the apply then."""

    apply_changes(workshop, assistant)
    workshop.run_queued_jobs()
    workshop.clock.advance(60)
    return read_apply(workshop, assistant, language)


def failed_checks(applied: JsonObject) -> list[JsonObject]:
    """The owner's checks a stopped apply names."""

    return [
        dict(check)
        for reason in applied["attention"]
        if reason["code"] == "checks_failed"
        for check in reason["failed_checks"]
    ]


def versions(workshop: Workshop, assistant: NewAssistant) -> list[JsonObject]:
    listed = workshop.client.get(
        f"{assistant.base}/assistant-versions", headers=assistant.headers
    )
    assert listed.status_code == 200, listed.text
    return cast(list[JsonObject], listed.json())


def build_draft(workshop: Workshop, assistant: NewAssistant) -> JsonObject:
    """A version built by hand and never checked: a draft."""

    built = workshop.client.post(
        f"{assistant.base}/assistant-versions",
        json={"run_autotests": False},
        headers=assistant.headers,
    )
    assert built.status_code == 201, built.text
    workshop.clock.advance(60)
    return dict(built.json())


def discard_draft(
    workshop: Workshop,
    assistant: NewAssistant,
    version_id: str,
    headers: dict[str, str] | None = None,
) -> Response:
    return workshop.client.delete(
        f"{assistant.base}/assistant/drafts/{version_id}",
        headers=assistant.headers if headers is None else headers,
    )
