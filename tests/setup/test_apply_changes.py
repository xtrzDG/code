"""'Apply changes': build, check in the background and publish in one call."""

from tests.e2e.harness import Workshop
from tests.setup.launch_steps import (
    NewAssistant,
    apply_changes,
    create_assistant,
    go_live,
    invite_staff,
    make_launch_ready,
    read_apply,
    read_setup,
    step_statuses,
)


def list_versions(
    workshop: Workshop, assistant: NewAssistant
) -> list[dict[str, object]]:
    listed = workshop.client.get(
        f"{assistant.base}/assistant-versions", headers=assistant.headers
    )
    assert listed.status_code == 200, listed.text
    return list(listed.json())


def audit_entities(workshop: Workshop, assistant: NewAssistant) -> list[str]:
    entries = workshop.client.get(
        f"{assistant.base}/audit-log", headers=assistant.headers
    ).json()["items"]
    return [str(entry["entity"]) for entry in entries]


def test_one_call_builds_checks_and_publishes(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)

    started = apply_changes(workshop, assistant)

    assert started["stage"] == "checking"
    assert started["is_in_progress"] is True
    assert started["version_number"] == 1
    assert started["checks_done"] == 0
    assert started["checks_total"] > 0
    assert started["attention"] == []
    versions = list_versions(workshop, assistant)
    assert [version["status"] for version in versions] == ["testing"]

    # The background worker plays the checks and publishes the version.
    workshop.run_queued_jobs()
    live = read_apply(workshop, assistant)

    assert live["stage"] == "live"
    assert live["is_in_progress"] is False
    assert live["has_unapplied_changes"] is False
    assert live["finished_at"] is not None
    assert live["checks_done"] is None
    business = workshop.client.get(assistant.base, headers=assistant.headers).json()
    assert business["status"] == "live"
    assert business["published_assistant_version_id"] == live["assistant_version_id"]
    assert "assistant_apply" in audit_entities(workshop, assistant)
    assert "assistant_version" in audit_entities(workshop, assistant)


def test_going_live_completes_the_setup(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)

    go_live(workshop, assistant)
    setup = read_setup(workshop, assistant)

    assert setup["is_live"] is True
    assert setup["is_complete"] is True
    assert step_statuses(setup)["launch"] == "done"
    assert setup["went_live_at"] is not None
    assert [milestone["kind"] for milestone in setup["milestones"]] == ["went_live"]
    assert setup["next_action"]["target"] in ("channels", "test_chat", "overview")
    assert setup["apply"]["stage"] == "live"


def test_applying_again_while_checking_starts_nothing_new(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    first = apply_changes(workshop, assistant)

    second = apply_changes(workshop, assistant)

    assert second["assistant_version_id"] == first["assistant_version_id"]
    assert second["stage"] == "checking"
    assert len(list_versions(workshop, assistant)) == 1


def test_applying_with_nothing_new_keeps_what_is_live(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    live = go_live(workshop, assistant)
    workshop.clock.advance(60)

    again = apply_changes(workshop, assistant)

    assert again["stage"] == "live"
    assert again["is_in_progress"] is False
    assert again["assistant_version_id"] == live["assistant_version_id"]
    assert len(list_versions(workshop, assistant)) == 1


def test_a_change_after_going_live_is_applied_as_a_new_version(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    first = go_live(workshop, assistant)
    workshop.clock.advance(60)
    # The owner opens a terrace. (The first checks' test bookings still hold
    # the three tables at the time the scripted customer always asks for.)
    terrace = workshop.client.post(
        f"{assistant.base}/resources",
        json={"name": "Терраса", "capacity": 4, "unit_count": 5},
        headers=assistant.headers,
    )
    assert terrace.status_code == 201, terrace.text

    pending = read_setup(workshop, assistant)
    workshop.clock.advance(60)
    second = go_live(workshop, assistant)

    assert pending["apply"]["has_unapplied_changes"] is True
    assert pending["next_action"]["target"] == "apply_changes"
    assert second["version_number"] == 2
    assert second["assistant_version_id"] != first["assistant_version_id"]
    statuses = {
        version["version_number"]: version["status"]
        for version in list_versions(workshop, assistant)
    }
    assert statuses == {1: "archived", 2: "published"}
    assert read_apply(workshop, assistant)["has_unapplied_changes"] is False


def test_staff_follow_the_progress_but_only_owners_apply(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    staff = invite_staff(workshop, assistant)

    refused = workshop.client.post(f"{assistant.base}/assistant/apply", headers=staff)
    before = workshop.client.get(f"{assistant.base}/assistant/apply", headers=staff)

    assert refused.status_code == 403
    assert before.status_code == 200
    assert before.json()["stage"] is None
    assert list_versions(workshop, assistant) == []
