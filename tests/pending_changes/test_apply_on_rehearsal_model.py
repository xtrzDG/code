"""'Apply changes' end to end on the model of LLM_PROVIDER=scripted."""

from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import (
    add_item,
    edit_item,
    read_pending,
)
from tests.setup.launch_steps import (
    apply_changes,
    create_assistant,
    go_live,
    make_launch_ready,
    read_apply,
)


def test_first_launch_and_a_price_change_go_live_on_the_rehearsal(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    item = add_item(
        workshop,
        assistant,
        {"kind": "menu_item", "title": "Хачапури", "price_minor": 1800},
    )
    first = go_live(workshop, assistant)
    assert first["stage"] == "live"
    assert read_pending(workshop, assistant)["count"] == 0

    edit_item(workshop, assistant, str(item["id"]), {"price_minor": 2000})
    pending = read_pending(workshop, assistant)
    print(pending)
    started = apply_changes(workshop, assistant)
    print(started)
    workshop.run_queued_jobs()
    after = read_apply(workshop, assistant)
    print(after)
    assert after["stage"] == "live", after
    assert read_pending(workshop, assistant)["count"] == 0
