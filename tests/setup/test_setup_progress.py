"""The guided setup derived from what a business has, and its optional steps."""

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import (
    NewAssistant,
    accept_dpa,
    add_staff_contact,
    create_assistant,
    fill_profile,
    invite_staff,
    read_setup,
    step_of,
    step_statuses,
)


def skip_step(
    workshop: Workshop,
    assistant: NewAssistant,
    step: str,
    headers: dict[str, str] | None = None,
) -> int:
    skipped = workshop.client.put(
        f"{assistant.base}/setup/skipped-steps/{step}",
        headers=headers or assistant.headers,
    )
    return skipped.status_code


def test_steps_are_done_as_the_business_fills_its_data(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    fill_profile(workshop, assistant)
    filled = read_setup(workshop, assistant)
    add_staff_contact(workshop, assistant)
    with_contact = read_setup(workshop, assistant)

    assert step_statuses(filled) == {
        "business": "done",
        "offer": "done",
        "hours_and_bookings": "done",
        "staff_contact": "next",
        "channels": "todo",
        "test": "todo",
        "launch": "todo",
    }
    assert filled["percent"] == 3 * 100 // 7
    assert filled["next_action"]["target"] == "staff_contacts"
    assert filled["can_go_live"] is False
    assert step_of(filled, "staff_contact")["missing"] == ["no_handoff_contact"]
    assert step_statuses(with_contact)["staff_contact"] == "done"
    assert with_contact["next_step"] == "channels"
    assert with_contact["minutes_left"] == sum(
        step["minutes"]
        for step in with_contact["steps"]
        if step["status"] in ("next", "todo")
    )


def test_the_launch_step_leads_through_the_agreement_to_applying(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)

    before = read_setup(workshop, assistant)
    accept_dpa(workshop, assistant)
    after = read_setup(workshop, assistant)

    assert step_of(before, "launch")["action"]["target"] == "agreement"
    assert before["can_go_live"] is False
    # No trial and no payment yet: the free trial starts at go-live.
    assert step_of(after, "launch")["action"]["target"] == "apply_changes"
    assert after["can_go_live"] is True
    assert after["is_live"] is False
    assert after["is_complete"] is False
    assert after["apply"]["has_unapplied_changes"] is True


def test_optional_steps_can_be_skipped_and_brought_back(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)

    assert skip_step(workshop, assistant, "channels") == 200
    skipped = read_setup(workshop, assistant)
    assert skip_step(workshop, assistant, "test") == 200
    both = read_setup(workshop, assistant)
    brought_back = workshop.client.delete(
        f"{assistant.base}/setup/skipped-steps/channels", headers=assistant.headers
    )
    restored = read_setup(workshop, assistant)

    assert step_statuses(skipped)["channels"] == "skipped"
    assert skipped["next_step"] == "test"
    # Skipped steps leave the share: 4 done of the 6 counted.
    assert skipped["percent"] == 4 * 100 // 6
    assert both["next_step"] == "launch"
    assert both["percent"] == 4 * 100 // 5
    assert brought_back.status_code == 204
    assert step_statuses(restored)["channels"] == "next"
    assert step_statuses(restored)["test"] == "skipped"


def test_skipping_twice_is_the_same_as_once(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    assert skip_step(workshop, assistant, "offer") == 200
    assert skip_step(workshop, assistant, "offer") == 200
    once_back = workshop.client.delete(
        f"{assistant.base}/setup/skipped-steps/offer", headers=assistant.headers
    )

    assert once_back.status_code == 204
    assert step_statuses(read_setup(workshop, assistant))["offer"] == "todo"


def test_steps_needed_to_go_live_cannot_be_skipped(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    for required in ("business", "hours_and_bookings", "staff_contact", "launch"):
        assert skip_step(workshop, assistant, required) == 422, required

    assert skip_step(workshop, assistant, "warp_drive") == 404
    assert "skipped" not in step_statuses(read_setup(workshop, assistant)).values()


def test_texts_follow_the_requested_language(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    russian = read_setup(workshop, assistant, language="ru")
    english = read_setup(workshop, assistant, language="en")

    assert russian["language"] == "ru"
    assert step_of(russian, "business")["title"] == "Ваш бизнес"
    assert step_of(english, "launch")["title"] == "Go live"
    assert english["next_action"]["label"]


def test_staff_follow_the_setup_but_only_owners_skip_steps(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    staff = invite_staff(workshop, assistant)

    read = workshop.client.get(f"{assistant.base}/setup", headers=staff)

    assert read.status_code == 200
    assert read.json()["next_step"] == "business"
    assert skip_step(workshop, assistant, "channels", headers=staff) == 403
    assert "skipped" not in step_statuses(read_setup(workshop, assistant)).values()
