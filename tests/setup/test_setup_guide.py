"""The guide after the launch, end to end: from a live assistant to customers."""

from typing import Any

from tests.e2e.harness import Workshop
from tests.e2e.journeys import BOOKING_REQUEST_RU
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    invite_staff,
    read_setup,
)
from tests.setup.test_activation_milestones import (
    celebrate,
    milestones,
    open_with_website_chat,
    write_from_the_website,
)


def guide(workshop: Workshop, assistant: NewAssistant) -> dict[str, Any]:
    return dict(read_setup(workshop, assistant)["guide"])


def after_launch(setup_guide: dict[str, Any]) -> dict[str, str]:
    return {
        str(step["code"]): str(step["status"])
        for step in setup_guide["steps_after_launch"]
    }


def test_before_the_launch_the_guide_leads_back_into_the_setup(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)

    started = guide(workshop, assistant)

    assert after_launch(started) == {
        "phone_test": "todo",
        "second_channel": "todo",
        "share": "todo",
    }
    assert started["next_step"] not in {"phone_test", "second_channel", "share"}
    assert started["is_complete"] is False
    assert started["minutes_left"] > 0
    refused = workshop.client.put(
        f"{assistant.base}/setup/guide-dismissal", headers=assistant.headers
    )
    assert refused.status_code == 409, refused.text


def test_a_message_while_the_guide_listens_completes_the_phone_check(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    assert guide(workshop, assistant)["next_step"] == "phone_test"

    listening = workshop.client.post(
        f"{assistant.base}/setup/phone-check", headers=assistant.headers
    )
    assert listening.status_code == 200, listening.text
    assert listening.json()["guide"]["is_phone_check_listening"] is True
    workshop.clock.advance(60)
    write_from_the_website(workshop, assistant, "Здравствуйте, вы открыты?")

    checked = guide(workshop, assistant)
    assert checked["phone_tested_at"] is not None
    assert checked["is_phone_check_listening"] is False
    assert after_launch(checked)["phone_test"] == "done"
    assert checked["next_step"] == "second_channel"


def test_a_conversation_outside_the_window_is_not_the_owners_test(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    workshop.client.post(
        f"{assistant.base}/setup/phone-check", headers=assistant.headers
    )
    workshop.clock.advance(31 * 60)

    write_from_the_website(workshop, assistant, "Здравствуйте")

    assert guide(workshop, assistant)["phone_tested_at"] is None


def test_the_qr_card_and_skips_finish_the_guide_and_the_owner_puts_it_away(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    staff = invite_staff(workshop, assistant)

    printed = workshop.client.post(
        f"{assistant.base}/setup/share-marks/printed_qr", headers=staff
    )
    assert printed.status_code == 204, printed.text
    assert after_launch(guide(workshop, assistant))["share"] == "done"
    for step in ("phone_test", "second_channel"):
        skipped = workshop.client.put(
            f"{assistant.base}/setup/skipped-steps/{step}", headers=assistant.headers
        )
        assert skipped.status_code == 200, skipped.text

    finished = guide(workshop, assistant)
    assert finished["is_complete"] is True
    assert finished["percent"] == 100
    by_staff = workshop.client.put(
        f"{assistant.base}/setup/guide-dismissal", headers=staff
    )
    assert by_staff.status_code == 403
    dismissed = workshop.client.put(
        f"{assistant.base}/setup/guide-dismissal", headers=assistant.headers
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["guide"]["is_dismissed"] is True
    back = workshop.client.delete(
        f"{assistant.base}/setup/guide-dismissal", headers=assistant.headers
    )
    assert back.status_code == 204
    assert guide(workshop, assistant)["is_dismissed"] is False


def test_the_first_visit_to_the_hosted_page_counts_as_shared(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    assert after_launch(guide(workshop, assistant))["share"] == "todo"

    page = workshop.client.get(f"/v1/public/chat/{assistant.business_id}")
    assert page.status_code == 200, page.text

    assert after_launch(guide(workshop, assistant))["share"] == "done"


def test_the_owners_turn_the_reminders_off_and_on(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    path = f"{assistant.base}/setup/reminders"

    assert workshop.client.get(path, headers=assistant.headers).json()["is_on"] is True
    off = workshop.client.put(path, json={"is_on": False}, headers=assistant.headers)
    assert off.status_code == 200, off.text
    assert off.json() == {"business_id": assistant.business_id, "is_on": False}
    assert workshop.client.get(path, headers=assistant.headers).json()["is_on"] is False
    on = workshop.client.put(path, json={"is_on": True}, headers=assistant.headers)
    assert on.json()["is_on"] is True


def test_the_first_booking_after_hours_is_a_milestone_celebrated_once(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    assert (
        celebrate(workshop, assistant, "first_after_hours_booking").status_code == 404
    )
    # Midnight in Tbilisi: the restaurant opens at 10:00.
    workshop.clock.advance(12 * 3600)
    write_from_the_website(workshop, assistant, BOOKING_REQUEST_RU)

    reached = milestones(workshop, assistant)
    assert {"first_booking", "first_after_hours_booking"} <= set(reached)
    assert reached["first_after_hours_booking"]["celebrated_at"] is None
    first = celebrate(workshop, assistant, "first_after_hours_booking")
    workshop.clock.advance(5)
    again = celebrate(workshop, assistant, "first_after_hours_booking")
    assert first.status_code == 200, first.text
    assert first.json()["celebrated_at"] is not None
    assert again.json()["celebrated_at"] == first.json()["celebrated_at"]
