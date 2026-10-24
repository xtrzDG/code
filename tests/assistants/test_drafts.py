"""
Drafts: versions built since the live one that customers never got. The
"Apply changes" sheet lists them, and the owner may discard one: it leaves
the list and the history, is written to the audit log, the test chat stops
choosing it and an apply never publishes it.
"""

from typing import cast

from tests.assistants.update_steps import (
    JsonObject,
    build_draft,
    discard_draft,
    launched,
    versions,
)
from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import add_item, read_pending
from tests.setup.launch_steps import apply_changes, invite_staff, read_apply


def test_a_draft_is_listed_and_discarded(workshop: Workshop) -> None:
    assistant = launched(workshop)
    draft = build_draft(workshop, assistant)

    listed = read_pending(workshop, assistant)["drafts"]
    discarded = discard_draft(workshop, assistant, str(draft["id"]))
    after = read_pending(workshop, assistant)
    audit = workshop.client.get(
        f"{assistant.base}/audit-log",
        params={"entity": "assistant_version", "action": "delete"},
        headers=assistant.headers,
    )

    assert [(item["assistant_version_id"], item["status"]) for item in listed] == [
        (draft["id"], "draft")
    ]
    assert listed[0]["version_number"] == 2
    assert (discarded.status_code, discarded.content) == (204, b"")
    assert after["drafts"] == []
    assert after["count"] == 0
    # Customers never had it, so nothing more is pending.
    assert after["has_unapplied_changes"] is False
    assert audit.status_code == 200, audit.text
    [entry] = cast(list[JsonObject], audit.json()["items"])
    assert (entry["action"], entry["entity_id"]) == ("delete", draft["id"])
    assert entry["ip_address"] == "testclient"
    # It leaves the history, but a link to it still opens.
    assert draft["id"] not in [
        version["id"] for version in versions(workshop, assistant)
    ]
    opened = workshop.client.get(
        f"{assistant.base}/assistant-versions/{draft['id']}", headers=assistant.headers
    )
    assert opened.status_code == 200, opened.text


def test_only_a_draft_customers_never_got_can_be_discarded(
    workshop: Workshop,
) -> None:
    assistant = launched(workshop)
    staff = invite_staff(workshop, assistant)
    draft = build_draft(workshop, assistant)
    live = read_apply(workshop, assistant)["assistant_version_id"]

    by_staff = discard_draft(workshop, assistant, str(draft["id"]), headers=staff)
    the_live_one = discard_draft(workshop, assistant, str(live))
    unknown = discard_draft(
        workshop, assistant, "assistant_version_00000000000000000000000000"
    )
    first = discard_draft(workshop, assistant, str(draft["id"]))
    again = discard_draft(workshop, assistant, str(draft["id"]))

    assert by_staff.status_code == 403
    assert the_live_one.status_code == 409
    assert unknown.status_code in {404, 422}
    assert first.status_code == 204
    assert again.status_code == 409


def test_the_test_chat_and_an_apply_leave_a_discarded_draft_alone(
    workshop: Workshop,
) -> None:
    assistant = launched(workshop)
    add_item(
        workshop,
        assistant,
        {"kind": "menu_item", "title": "Пхали", "price_minor": 900},
    )
    workshop.clock.advance(60)
    draft = build_draft(workshop, assistant)
    assert discard_draft(workshop, assistant, str(draft["id"])).status_code == 204

    chatted = workshop.client.post(
        f"{assistant.base}/test-chat",
        json={"text": "Здравствуйте!", "session_key": "drafts-1"},
        headers=assistant.headers,
    )
    started = apply_changes(workshop, assistant)

    assert chatted.status_code == 200, chatted.text
    # The test chat built a fresh preview with the new dish instead.
    assert chatted.json()["assistant_version_id"] not in {draft["id"], None}
    assert started["stage"] == "checking", started
    assert started["assistant_version_id"] != draft["id"]


def test_a_draft_under_test_is_not_discarded(workshop: Workshop) -> None:
    assistant = launched(workshop)
    add_item(
        workshop,
        assistant,
        {"kind": "menu_item", "title": "Пхали", "price_minor": 900},
    )
    workshop.clock.advance(60)
    started = apply_changes(workshop, assistant)

    refused = discard_draft(workshop, assistant, str(started["assistant_version_id"]))

    assert started["stage"] == "checking"
    assert refused.status_code == 409
    assert refused.json()["error"] == "conflict"
