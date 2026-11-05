"""
A closing business stays closed until its closure is cancelled: publishing
or rolling back an assistant version never makes it live again, and no
channel is connected again; the closure is untouched by every refusal.
"""

from typing import Any, cast

from tests.business_closures.closure_world import ClosureWorld, open_closure_world
from tests.business_closures.test_business_deletion_journey import (
    business_status,
    channel_statuses,
)


def versions_of(world: ClosureWorld) -> list[dict[str, Any]]:
    listed = world.workshop.client.get(
        f"/v1/businesses/{world.business_b}/assistant-versions",
        headers=world.owner_b,
    )
    assert listed.status_code == 200, listed.text
    body: Any = listed.json()
    if isinstance(body, dict):
        return cast(list[dict[str, Any]], cast(dict[str, Any], body)["items"])

    return cast(list[dict[str, Any]], body)


def assert_still_closing(world: ClosureWorld) -> None:
    assert business_status(world) == "paused"
    assert "connected" not in channel_statuses(world).values()
    closure = world.workshop.client.get(world.closure_path, headers=world.owner_b)
    assert closure.json()["state"] == "pending_deletion"


def test_a_rollback_does_not_make_a_closing_business_live() -> None:
    with open_closure_world() as world:
        archived = next(v for v in versions_of(world) if v["status"] == "archived")
        world.close_b()

        rolled_back = world.workshop.client.post(
            f"/v1/businesses/{world.business_b}/assistant-versions/"
            f"{archived['id']}/rollback",
            headers=world.owner_b,
        )

        assert rolled_back.status_code == 409, rolled_back.text
        assert "closing" in rolled_back.text
        assert_still_closing(world)


def test_publishing_does_not_make_a_closing_business_live() -> None:
    with open_closure_world() as world:
        base = f"/v1/businesses/{world.business_b}"
        assembled = world.workshop.client.post(
            f"{base}/assistant-versions", json={}, headers=world.owner_b
        )
        assert assembled.status_code == 201, assembled.text
        # The worker plays the new version's autotests.
        world.workshop.container.gateways.background_worker().run_once()
        world.close_b()

        published = world.workshop.client.post(
            f"/v1/businesses/{world.business_b}/assistant-versions/"
            f"{assembled.json()['id']}/publish",
            json={},
            headers=world.owner_b,
        )

        assert published.status_code == 409, published.text
        assert "closing" in published.text
        assert_still_closing(world)


def test_a_channel_is_not_connected_while_closing() -> None:
    with open_closure_world() as world:
        world.close_b()

        connected = world.workshop.client.put(
            f"/v1/businesses/{world.business_b}/channels/web",
            json={},
            headers=world.owner_b,
        )

        assert connected.status_code == 409, connected.text
        assert "closing" in connected.text
        assert_still_closing(world)
        # Cancelling brings everything back.
        kept = world.workshop.client.delete(world.closure_path, headers=world.owner_b)
        assert kept.status_code == 204, kept.text
        again = world.workshop.client.put(
            f"/v1/businesses/{world.business_b}/channels/web",
            json={},
            headers=world.owner_b,
        )
        assert again.status_code == 200, again.text
