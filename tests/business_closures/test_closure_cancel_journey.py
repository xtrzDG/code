"""
Cancelling a closure within its 30 days brings the business back as it
was, and the closure refuses what it must: the wrong name, staff, other
businesses' owners, an old sign-in, and a cancel once the deletion began.
"""

from dataclasses import replace

from tests.business_closures.closure_world import (
    DAY_SECONDS,
    DEMO_RESTAURANT,
    ClosureWorld,
    open_closure_world,
)
from tests.business_closures.test_business_deletion_journey import (
    business_status,
    channel_statuses,
)

STEP_UP_SECONDS: int = 11 * 60


def cancel(world: ClosureWorld) -> int:
    return world.workshop.client.delete(
        world.closure_path, headers=world.owner_b
    ).status_code


def test_cancelling_the_closure_restores_the_business() -> None:
    with open_closure_world() as world:
        channels_before = channel_statuses(world)
        world.close_b()
        world.workshop.clock.advance(5 * 60)

        assert cancel(world) == 204

        view = world.workshop.client.get(world.closure_path, headers=world.owner_b)
        assert view.json()["state"] == "active"
        assert business_status(world) == "live"
        assert channel_statuses(world) == channels_before
        assert cancel(world) == 404
        world.workshop.clock.advance(31 * DAY_SECONDS)
        world.tick("queue_business_deletions")
        world.workshop.run_queued_jobs()
        assert world.rows_of(world.business_b)["businesses"] == 1


def test_a_cancel_after_the_paid_period_waits_paused_for_a_plan() -> None:
    with open_closure_world() as world:
        channels_before = channel_statuses(world)
        world.close_b()
        world.workshop.clock.advance(20 * DAY_SECONDS)
        owner = world.sign_in_owner_b()
        back = replace(world, owner_b=owner)

        assert cancel(back) == 204

        # The closure stopped the subscription, so the assistant may not go
        # live again until the owner pays; everything else is back.
        assert business_status(back) == "paused"
        assert channel_statuses(back) == channels_before
        assert world.rows_of(world.business_b)["contacts"] > 0


def test_closing_twice_opens_one_closure() -> None:
    with open_closure_world() as world:
        first = world.close_b()
        world.workshop.clock.advance(60)

        second = world.close_b()

        assert second["delete_after"] == first["delete_after"]
        assert second["requested_at"] == first["requested_at"]


def test_the_closure_refuses_the_wrong_name_staff_and_strangers() -> None:
    with open_closure_world() as world:
        client = world.workshop.client
        wrong = client.post(
            world.closure_path,
            json={"confirmation_name": "Another place"},
            headers=world.owner_b,
        )
        staff = client.post(
            world.closure_path,
            json={"confirmation_name": DEMO_RESTAURANT},
            headers=world.staff_b,
        )
        stranger = client.post(
            world.closure_path,
            json={"confirmation_name": DEMO_RESTAURANT},
            headers=world.owner_a,
        )

        assert wrong.status_code == 422
        assert staff.status_code == 403
        assert stranger.status_code == 404
        assert client.get(world.closure_path, headers=world.owner_b).json()[
            "state"
        ] == ("active")


def test_closing_needs_a_fresh_sign_in() -> None:
    with open_closure_world() as world:
        world.workshop.clock.advance(STEP_UP_SECONDS)

        closed = world.workshop.client.post(
            world.closure_path,
            json={"confirmation_name": DEMO_RESTAURANT},
            headers=world.owner_b,
        )

        assert closed.status_code == 401
        assert closed.json()["reasons"][0]["code"] == "step_up_required"


def test_a_queued_deletion_can_no_longer_be_cancelled() -> None:
    with open_closure_world() as world:
        world.close_b()
        world.workshop.clock.advance(31 * DAY_SECONDS)
        owner = world.sign_in_owner_b()

        world.tick("queue_business_deletions")

        view = world.workshop.client.get(world.closure_path, headers=owner)
        assert view.json()["state"] == "deleting"
        assert view.json()["can_cancel"] is False
        refused = world.workshop.client.delete(world.closure_path, headers=owner)
        assert refused.status_code == 409
