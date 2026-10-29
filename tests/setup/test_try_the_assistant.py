"""'Try your assistant' before going live, and from the owner's phone."""

from typing import Any

from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import API_BASE_URL
from tests.e2e.journeys import BUSINESS_BOT_TOKEN
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    fill_profile,
    go_live,
    invite_staff,
    make_launch_ready,
    read_setup,
    step_statuses,
)


def send_test_message(
    workshop: Workshop,
    assistant: NewAssistant,
    text: str = "Здравствуйте!",
    headers: dict[str, str] | None = None,
) -> Any:
    return workshop.client.post(
        f"{assistant.base}/test-chat",
        json={"text": text},
        headers=headers or assistant.headers,
    )


def version_numbers(workshop: Workshop, assistant: NewAssistant) -> list[int]:
    listed = workshop.client.get(
        f"{assistant.base}/assistant-versions", headers=assistant.headers
    ).json()
    return sorted(int(version["version_number"]) for version in listed)


def test_the_owner_tries_the_assistant_before_going_live(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    too_early = send_test_message(workshop, assistant)
    fill_profile(workshop, assistant)

    reply = send_test_message(workshop, assistant)
    again = send_test_message(workshop, assistant, "А парковка есть?")

    assert too_early.status_code == 409
    assert reply.status_code == 200, reply.text
    assert reply.json()["assistant_version_number"] == 1
    assert again.json()["assistant_version_number"] == 1
    # A preview only: nothing went live and nothing was checked.
    assert version_numbers(workshop, assistant) == [1]
    setup = read_setup(workshop, assistant)
    assert step_statuses(setup)["test"] == "done"
    assert [row["kind"] for row in setup["milestones"]] == ["test_chat_tried"]
    assert setup["is_live"] is False


def test_the_test_chat_follows_the_latest_edits(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    send_test_message(workshop, assistant)
    workshop.clock.advance(60)
    edited = workshop.client.patch(
        f"{assistant.base}/profile",
        json={"tone": "Коротко и с юмором"},
        headers=assistant.headers,
    )
    assert edited.status_code == 200, edited.text

    reply = send_test_message(workshop, assistant)

    assert reply.json()["assistant_version_number"] == 2
    assert version_numbers(workshop, assistant) == [1, 2]


def test_staff_test_only_versions_the_owner_built(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    staff = invite_staff(workshop, assistant)

    before = send_test_message(workshop, assistant, headers=staff)
    send_test_message(workshop, assistant)
    after = send_test_message(workshop, assistant, headers=staff)

    assert before.status_code == 409
    assert after.status_code == 200, after.text
    assert version_numbers(workshop, assistant) == [1]


def test_phone_links_open_the_website_chat_and_the_telegram_bot(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    assert read_setup(workshop, assistant)["phone_test_links"] == []
    web_chat = workshop.client.put(
        f"{assistant.base}/channels/web", json={}, headers=assistant.headers
    )
    telegram = workshop.client.put(
        f"{assistant.base}/channels/telegram",
        json={"bot_token": BUSINESS_BOT_TOKEN},
        headers=assistant.headers,
    )
    assert web_chat.status_code == 200, web_chat.text
    assert telegram.status_code == 200, telegram.text

    before = read_setup(workshop, assistant)
    go_live(workshop, assistant)
    after = read_setup(workshop, assistant)

    assert step_statuses(before)["channels"] == "done"
    assert before["phone_test_links"] == [
        {
            "channel": "web_chat",
            "url": f"{API_BASE_URL}/widget/demo?business_id="
            f"{assistant.business_id}&language=ka",
            "is_answering": False,
        },
        {
            "channel": "telegram",
            "url": "https://t.me/workshop_bot",
            "is_answering": False,
        },
    ]
    assert [link["is_answering"] for link in after["phone_test_links"]] == [
        True,
        True,
    ]
    demo = workshop.client.get(
        "/widget/demo",
        params={"business_id": assistant.business_id, "language": "ka"},
    )
    assert demo.status_code == 200
    assert assistant.business_id in demo.text
