"""
"Apply changes" end to end over the API on the rehearsal model of
LLM_PROVIDER=scripted (what development, staging and the cabinet's
end-to-end suite run): the first launch passes every check, a new price
is listed in the owner's words, applied after a quick check, and the
test bookings of the first checks no longer hold the tables.
"""

from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import add_item, edit_item, read_pending
from tests.setup.launch_steps import (
    apply_changes,
    create_assistant,
    go_live,
    invite_staff,
    make_launch_ready,
    read_apply,
)


def test_a_new_price_goes_live_after_the_first_launch(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    item = add_item(
        workshop,
        assistant,
        {"kind": "menu_item", "title": "Хачапури", "price_minor": 1800},
    )
    before_launch = read_pending(workshop, assistant)
    first = go_live(workshop, assistant)

    assert before_launch["is_live"] is False and before_launch["changes"] == []
    assert first["stage"] == "live"
    assert read_pending(workshop, assistant)["count"] == 0

    workshop.clock.advance(60)
    edit_item(workshop, assistant, str(item["id"]), {"price_minor": 2000})
    pending = read_pending(workshop, assistant, "ru")
    assert pending["is_live"] is True
    assert pending["count"] == 1
    change = pending["changes"][0]
    assert (change["area"], change["action"], change["detail"]) == (
        "offer",
        "changed",
        "price",
    )
    assert (change["subject"], change["before"], change["after"]) == (
        "Хачапури",
        "18.00 GEL",
        "20.00 GEL",
    )

    started = apply_changes(workshop, assistant)
    workshop.run_queued_jobs()
    applied = read_apply(workshop, assistant)

    # The booking check passes again: the first checks' test bookings hold nothing.
    assert started["checks_total"] == 4
    assert applied["stage"] == "live", applied
    assert applied["version_number"] == 2
    assert read_pending(workshop, assistant)["count"] == 0


def test_staff_see_the_pending_changes_and_others_do_not(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    staff = invite_staff(workshop, assistant)
    stranger = create_assistant(workshop, phone="+995 555 12 34 99")

    seen = workshop.client.get(
        f"{assistant.base}/assistant/pending-changes", headers=staff
    )
    hidden = workshop.client.get(
        f"{assistant.base}/assistant/pending-changes", headers=stranger.headers
    )

    assert seen.status_code == 200
    assert seen.json()["business_id"] == assistant.business_id
    assert hidden.status_code == 404
