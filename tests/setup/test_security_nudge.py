"""
The reminder "Protect your customers' data: turn on a second factor" over
the real API: shown to the owner of a live business without a passkey or an
authenticator app, put away by them, and back once the team grows.
"""

from typing import Any

from tests.e2e.harness import Workshop
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.setup.launch_steps import NewAssistant, create_assistant, invite_staff
from tests.setup.test_activation_milestones import open_with_website_chat
from tests.setup.test_setup_guide import after_launch, guide
from tests.users.mfa.mfa_api import set_up_authenticator

type JsonObject = dict[str, Any]


def nudge(
    workshop: Workshop, assistant: NewAssistant, headers: dict[str, str] | None = None
) -> JsonObject:
    read = workshop.client.get(
        f"{assistant.base}/security-nudge", headers=headers or assistant.headers
    )
    assert read.status_code == 200, read.text
    return dict(read.json())


def put_away(
    workshop: Workshop, assistant: NewAssistant, headers: dict[str, str] | None = None
) -> int:
    return workshop.client.put(
        f"{assistant.base}/security-nudge/dismissal",
        headers=headers or assistant.headers,
    ).status_code


def test_before_the_launch_the_owner_is_not_reminded_yet(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    reminder = nudge(workshop, assistant)

    assert reminder["is_shown"] is False
    assert reminder["reason"] is None
    assert reminder["is_owner"] is True
    assert reminder["has_second_factor"] is False
    assert reminder["team_size"] == 1


def test_after_the_launch_the_owner_without_a_second_factor_is_reminded(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)

    reminder = nudge(workshop, assistant)

    assert reminder["is_shown"] is True
    assert reminder["reason"] == "protect_customers"
    assert reminder["dismissed_at"] is None
    assert after_launch(guide(workshop, assistant))["protect_data"] == "todo"


def test_staff_are_not_reminded_and_cannot_put_the_owners_reminder_away(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)
    staff = invite_staff(workshop, assistant)

    reminder = nudge(workshop, assistant, staff)

    assert reminder["is_shown"] is False
    assert reminder["is_owner"] is False
    assert reminder["team_size"] == 2
    assert put_away(workshop, assistant, staff) == 403
    staff_guide = workshop.client.get(f"{assistant.base}/setup", headers=staff)
    assert staff_guide.status_code == 200, staff_guide.text
    assert "protect_data" not in after_launch(staff_guide.json()["guide"])
    assert nudge(workshop, assistant)["is_shown"] is True


def test_put_away_by_an_owner_alone_it_comes_back_when_the_team_grows(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)

    assert put_away(workshop, assistant) == 200
    hidden = nudge(workshop, assistant)
    assert hidden["is_shown"] is False
    assert hidden["dismissed_at"] is not None
    assert after_launch(guide(workshop, assistant))["protect_data"] == "skipped"

    invite_staff(workshop, assistant)
    back = nudge(workshop, assistant)
    assert back["is_shown"] is True
    assert back["reason"] == "team_grew"
    assert after_launch(guide(workshop, assistant))["protect_data"] == "todo"

    assert put_away(workshop, assistant) == 200
    assert nudge(workshop, assistant)["is_shown"] is False
    assert after_launch(guide(workshop, assistant))["protect_data"] == "skipped"


def test_an_owner_with_an_authenticator_app_has_done_the_step(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)

    set_up_authenticator(workshop, assistant.token, GEORGIAN_OWNER_PHONE)

    reminder = nudge(workshop, assistant)
    assert reminder["is_shown"] is False
    assert reminder["has_second_factor"] is True
    assert after_launch(guide(workshop, assistant))["protect_data"] == "done"


def test_the_step_is_put_away_with_the_reminder_not_as_a_skipped_step(
    workshop: Workshop,
) -> None:
    assistant = open_with_website_chat(workshop)

    skipped = workshop.client.put(
        f"{assistant.base}/setup/skipped-steps/protect_data",
        headers=assistant.headers,
    )

    assert skipped.status_code in {404, 422}, skipped.text
    assert nudge(workshop, assistant)["is_shown"] is True
