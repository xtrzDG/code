"""
Steps of teaching a live assistant over the real API: a website visitor's
question, "Fix this answer", the owner's checks and the next "Apply
changes".
"""

from dataclasses import dataclass
from typing import Any, cast

from tests.e2e.harness import Workshop
from tests.e2e.journeys import WIDGET_SESSION
from tests.e2e.widget_turns import ask_widget
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    go_live,
    make_launch_ready,
)

type JsonObject = dict[str, Any]

CAKE_QUESTION: str = "Можно прийти со своим тортом?"
CAKE_ANSWER: str = "Да, со своим тортом можно, подадим его бесплатно."


@dataclass(frozen=True)
class AskedAnswer:
    """The assistant's answer to a website visitor, as the cabinet names it."""

    conversation_id: str
    message_id: str
    text: str

    def path(self, assistant: NewAssistant) -> str:
        return (
            f"{assistant.base}/conversations/{self.conversation_id}"
            f"/messages/{self.message_id}/correction"
        )


def live_assistant(workshop: Workshop) -> NewAssistant:
    """A launched restaurant whose website chat is on."""

    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    go_live(workshop, assistant)
    web_chat = workshop.client.put(
        f"{assistant.base}/channels/web", json={}, headers=assistant.headers
    )
    assert web_chat.status_code == 200, web_chat.text
    workshop.clock.advance(60)
    return assistant


def ask(
    workshop: Workshop,
    assistant: NewAssistant,
    text: str,
    session_key: str = WIDGET_SESSION,
) -> AskedAnswer:
    answer: JsonObject = ask_widget(workshop, assistant.business_id, session_key, text)
    assert answer["message_id"] is not None, answer
    workshop.clock.advance(60)
    return AskedAnswer(
        conversation_id=str(answer["conversation_id"]),
        message_id=str(answer["message_id"]),
        text=str(answer["text"]),
    )


def correct(
    workshop: Workshop,
    assistant: NewAssistant,
    answer: AskedAnswer,
    body: JsonObject,
) -> JsonObject:
    corrected = workshop.client.post(
        answer.path(assistant), json=body, headers=assistant.headers
    )
    assert corrected.status_code == 200, corrected.text
    workshop.clock.advance(60)
    return dict(corrected.json())


def pending_changes(workshop: Workshop, assistant: NewAssistant) -> list[JsonObject]:
    read = workshop.client.get(
        f"{assistant.base}/assistant/pending-changes", headers=assistant.headers
    )
    assert read.status_code == 200, read.text
    return cast(list[JsonObject], read.json()["changes"])


def save_check(
    workshop: Workshop, assistant: NewAssistant, body: JsonObject
) -> JsonObject:
    saved = workshop.client.post(
        f"{assistant.base}/autotest-cases", json=body, headers=assistant.headers
    )
    assert saved.status_code == 201, saved.text
    workshop.clock.advance(60)
    return dict(saved.json())


def list_checks(workshop: Workshop, assistant: NewAssistant) -> list[JsonObject]:
    listed = workshop.client.get(
        f"{assistant.base}/autotest-cases", headers=assistant.headers
    )
    assert listed.status_code == 200, listed.text
    return cast(list[JsonObject], listed.json()["items"])


def autotest_results(
    workshop: Workshop, assistant: NewAssistant, version_id: str
) -> list[JsonObject]:
    run = workshop.client.get(
        f"{assistant.base}/assistant-versions/{version_id}/autotest-run",
        headers=assistant.headers,
    )
    assert run.status_code == 200, run.text
    return cast(list[JsonObject], run.json()["results"])
