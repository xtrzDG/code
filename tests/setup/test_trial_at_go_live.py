"""The free trial starts when the assistant first goes live, not at sign-up."""

from typing import Any

from app.registries.billing.plan_catalog import TRIAL_DAYS
from tests.e2e.harness import Workshop
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    go_live,
    make_launch_ready,
    read_setup,
)

DAY_MICROSECONDS: int = 86_400 * 1_000_000


def billing(workshop: Workshop, assistant: NewAssistant) -> dict[str, Any]:
    overview = workshop.client.get(
        f"{assistant.base}/billing", headers=assistant.headers
    )
    assert overview.status_code == 200, overview.text
    return dict(overview.json())


def test_the_trial_waits_for_the_go_live(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)

    before = billing(workshop, assistant)

    assert before["subscription"] is None
    assert before["is_trial_available"] is True
    assert before["does_trial_start_at_go_live"] is True
    assert read_setup(workshop, assistant)["trial_ends_at"] is None


def test_going_live_starts_every_trial_day(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    # The owner took a few hours over the setup.
    workshop.clock.advance(6 * 3600)

    go_live(workshop, assistant)
    after = billing(workshop, assistant)
    setup = read_setup(workshop, assistant)

    subscription = after["subscription"]
    assert subscription["status"] == "trialing"
    assert subscription["plan_key"] == assistant.created["business"]["plan_key"]
    assert subscription["billing_period"] == "monthly"
    assert subscription["period_start"] == setup["went_live_at"]
    # Tbilisi keeps no daylight saving time, so the days are exact.
    assert subscription["trial_ends_at"] == (
        setup["went_live_at"] + int(TRIAL_DAYS) * DAY_MICROSECONDS
    )
    assert setup["trial_ends_at"] == subscription["trial_ends_at"]
    assert after["is_trial_available"] is False
    assert after["does_trial_start_at_go_live"] is False
    business = workshop.client.get(assistant.base, headers=assistant.headers).json()
    assert business["service_mode"] == "full"


def test_a_trial_the_owner_started_earlier_is_kept(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    started = workshop.client.post(
        f"{assistant.base}/billing/trial", json={}, headers=assistant.headers
    )
    assert started.status_code == 201, started.text
    trial = started.json()["subscription"]
    assert billing(workshop, assistant)["does_trial_start_at_go_live"] is False
    workshop.clock.advance(6 * 3600)

    go_live(workshop, assistant)

    kept = billing(workshop, assistant)["subscription"]
    assert kept["id"] == trial["id"]
    assert kept["trial_ends_at"] == trial["trial_ends_at"]
    assert kept["period_start"] == trial["period_start"]


def test_the_readiness_check_says_the_trial_starts_at_go_live(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    make_launch_ready(workshop, assistant)
    version = workshop.client.post(
        f"{assistant.base}/assistant-versions",
        json={"run_autotests": False},
        headers=assistant.headers,
    )
    assert version.status_code == 201, version.text

    readiness = workshop.client.get(
        f"{assistant.base}/assistant-versions/{version.json()['id']}/go-live-readiness",
        headers=assistant.headers,
    )

    assert readiness.status_code == 200, readiness.text
    check = next(
        row
        for row in readiness.json()["checks"]
        if row["code"] == "subscription_or_trial"
    )
    assert check["is_ok"] is True
    assert check["details"] == ["trial_at_go_live"]
    assert check["message"] == "The free trial starts when the assistant goes live."
