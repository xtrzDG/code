"""
A close that meets a cancel still restoring the business is refused, so
the cancel's last step never removes a closure it did not take; a
cancelled closure left by a cancel that died is replaced once the
cancel's lease is over.
"""

from typing import Any

import pytest
from typed_time_provider import Microseconds

from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.businesses.closure.closure_cancellation import (
    take_pending_closure,
)
from app.use_cases.businesses.closure.closure_effects import ClosureEffects
from tests.business_closures.closure_world import (
    DEMO_RESTAURANT,
    ClosureWorld,
    open_closure_world,
)
from tests.business_closures.test_business_deletion_journey import business_status

LEASE_SECONDS: int = 10 * 60


def close(world: ClosureWorld, headers: dict[str, str]) -> Any:
    return world.workshop.client.post(
        world.closure_path,
        json={"confirmation_name": DEMO_RESTAURANT},
        headers=headers,
    )


def closure_state(world: ClosureWorld) -> str:
    view = world.workshop.client.get(world.closure_path, headers=world.owner_b)
    return str(view.json()["state"])


def test_a_close_during_a_cancels_restore_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with open_closure_world() as world:
        world.close_b()
        world.workshop.clock.advance(60)
        answers: list[int] = []
        restore = ClosureEffects.restore

        def restore_with_a_close_in_between(
            effects: ClosureEffects,
            closure: BusinessClosureDocument,
            now: Microseconds,
        ) -> None:
            # Another tab (or owner) closes the business while this cancel
            # restores it.
            answers.append(close(world, world.owner_b).status_code)
            restore(effects, closure, now)

        monkeypatch.setattr(ClosureEffects, "restore", restore_with_a_close_in_between)

        cancelled = world.workshop.client.delete(
            world.closure_path, headers=world.owner_b
        )

        assert cancelled.status_code == 204, cancelled.text
        assert answers == [409]
        assert closure_state(world) == "active"
        assert business_status(world) == "live"


def test_a_cancel_that_died_is_replaced_after_its_lease() -> None:
    with open_closure_world() as world:
        world.close_b()
        container = world.workshop.container
        with container.utilities.storage_scope().platform_wide():
            taken = take_pending_closure(
                container.repositories.business_closure_repo(),
                BusinessId(world.business_b),
                world.now(),
            )
        assert taken is not None
        assert closure_state(world) == "active"

        assert close(world, world.owner_b).status_code == 409

        world.workshop.clock.advance(LEASE_SECONDS + 1)
        closed = close(world, world.sign_in_owner_b())
        assert closed.status_code == 200, closed.text
        assert closed.json()["state"] == "pending_deletion"
