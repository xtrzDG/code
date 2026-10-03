"""Milestones on the way to real customers, each recorded and celebrated once."""

from typing import Any

from tests.e2e.harness import Workshop
from tests.e2e.journeys import BOOKING_REQUEST_RU, WIDGET_SESSION
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    go_live,
    invite_staff,
    make_launch_ready,
    read_setup,
)


def milestones(workshop: Workshop, assistant: NewAssistant) -> dict[str, Any]:
    return {
        str(row["kind"]): row for row in read_setup(workshop, assistant)["milestones"]
    }


def celebrate(
    workshop: Workshop,
    assistant: NewAssistant,
    kind: str,
    headers: dict[str, str] | None = None,
) -> Any:
    return workshop.client.post(
        f"{assistant.base}/setup/milestones/{kind}/celebrate",
        headers=headers or assistant.headers,
    )


def write_from_the_website(
    workshop: Workshop, assistant: NewAssistant, text: str
) -> dict[str, Any]:
    sent = workshop.client.post(
        f"/v1/widget/{assistant.business_id}/messages",
        json={"session_key": WIDGET_SESSION, "text": text},
    )
    assert sent.status_code == 200, sent.text
    return dict(sent.json())


def open_with_website_chat(workshop: Workshop) -> NewAssistant:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    web_chat = workshop.client.put(
        f"{assistant.base}/channels/web", json={}, headers=assistant.headers
    )
    assert web_chat.status_code == 200, web_chat.text
    go_live(workshop, assistant)
    return assistant


def test_the_first_real_conversation_booking_and_handoff_are_milestones(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    went_live = milestones(workshop, assistant)["went_live"]["occurred_at"]
    # The automatic checks talked, booked and handed off in the sandbox:
    # none of that is a milestone.
    assert set(milestones(workshop, assistant)) == {"went_live"}

    workshop.clock.advance(600)
    booked = write_from_the_website(workshop, assistant, BOOKING_REQUEST_RU)
    workshop.clock.advance(600)
    handed_off = write_from_the_website(workshop, assistant, "Позовите менеджера")

    reached = milestones(workshop, assistant)
    assert booked["is_handed_off"] is False
    assert handed_off["is_handed_off"] is True
    assert set(reached) == {
        "went_live",
        "first_conversation",
        "first_booking",
        "first_handoff",
    }
    # Each keeps the moment it really happened, not when it was noticed.
    assert reached["first_conversation"]["occurred_at"] == went_live + 600_000_000
    assert reached["first_booking"]["occurred_at"] == went_live + 600_000_000
    assert reached["first_handoff"]["occurred_at"] == went_live + 1_200_000_000
    assert all(row["celebrated_at"] is None for row in reached.values())


def test_a_milestone_is_celebrated_once(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    go_live(workshop, assistant)

    workshop.clock.advance(5)
    first = celebrate(workshop, assistant, "went_live")
    workshop.clock.advance(5)
    again = celebrate(workshop, assistant, "went_live")

    assert first.status_code == 200, first.text
    assert first.json()["kind"] == "went_live"
    assert first.json()["celebrated_at"] is not None
    assert again.json()["celebrated_at"] == first.json()["celebrated_at"]
    shown = milestones(workshop, assistant)["went_live"]
    assert shown["celebrated_at"] == first.json()["celebrated_at"]


def test_a_milestone_not_reached_cannot_be_celebrated(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    not_yet = celebrate(workshop, assistant, "first_booking")
    unknown = celebrate(workshop, assistant, "first_million")

    assert not_yet.status_code == 404
    assert unknown.status_code == 404
    assert milestones(workshop, assistant) == {}


def test_staff_see_and_celebrate_milestones_too(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    go_live(workshop, assistant)
    staff = invite_staff(workshop, assistant)

    celebrated = celebrate(workshop, assistant, "went_live", headers=staff)

    assert celebrated.status_code == 200, celebrated.text
    assert celebrated.json()["celebrated_at"] is not None


def test_a_business_live_before_milestones_existed_gets_its_go_live_back(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    go_live(workshop, assistant)
    went_live = milestones(workshop, assistant)["went_live"]["occurred_at"]
    # As if it had gone live before milestones were recorded.
    container = workshop.container
    collection = container.adapters.launch_collections.activation_event_collection()
    with container.utilities.storage_scope().platform_wide():
        for event in collection.list_all():
            collection.delete(str(event.id))
    workshop.clock.advance(3600)

    restored = milestones(workshop, assistant)

    assert set(restored) == {"went_live"}
    assert restored["went_live"]["occurred_at"] == went_live
