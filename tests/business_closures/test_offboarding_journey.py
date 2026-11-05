"""
Automatic offboarding (DPA 13.3): OFFBOARD_AFTER_DAYS after a subscription
ended unpaid the business closes by itself; paying again reopens it; a
business that never paid is left alone.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.business_closures.closure_world import (
    DAY_SECONDS,
    STRANGER_OWNER_PHONE,
    ClosureWorld,
    open_closure_world,
)
from tests.e2e.harness import bearer

MICROSECONDS_PER_DAY: int = DAY_SECONDS * 1_000_000


def change_subscription(
    world: ClosureWorld, change: Callable[[SubscriptionDocument, int], None]
) -> None:
    business_id = BusinessId(world.business_a)
    container = world.workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        repo = container.repositories.subscription_repo()
        [subscription] = repo.list_by_business(business_id)
        change(subscription, int(world.now()))
        repo.save(subscription)


def miss_the_payment(subscription: SubscriptionDocument, now: int) -> None:
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = Microseconds(now)


def pay(subscription: SubscriptionDocument, now: int) -> None:
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.grace_until = None
    subscription.period_start = Microseconds(now)
    subscription.period_end = Microseconds(now + 30 * MICROSECONDS_PER_DAY)


def closure_of_a(world: ClosureWorld) -> dict[str, object]:
    owner = bearer(world.workshop.sign_in_with_phone(STRANGER_OWNER_PHONE)[0])
    world.workshop.clock.advance(60)
    view = world.workshop.client.get(
        f"/v1/businesses/{world.business_a}/closure", headers=owner
    )
    assert view.status_code == 200, view.text
    result: dict[str, object] = view.json()
    return result


def start_trial_of_a(world: ClosureWorld) -> None:
    trial = world.workshop.client.post(
        f"/v1/businesses/{world.business_a}/billing/trial",
        json={},
        headers=world.owner_a,
    )
    assert trial.status_code == 201, trial.text


def test_an_unpaid_business_closes_after_the_offboarding_days() -> None:
    with open_closure_world() as world:
        start_trial_of_a(world)
        change_subscription(world, miss_the_payment)
        world.workshop.clock.advance(29 * DAY_SECONDS)
        world.tick("offboard_unpaid_businesses")
        assert closure_of_a(world)["state"] == "active"

        world.workshop.clock.advance(2 * DAY_SECONDS)
        world.tick("offboard_unpaid_businesses")

        view = closure_of_a(world)
        assert view["state"] == "pending_deletion"
        assert view["reason"] == "unpaid_subscription"
        assert view["can_cancel"] is False
        assert view["actor_name"] is None


def test_paying_again_reopens_a_business_closed_for_non_payment() -> None:
    with open_closure_world() as world:
        start_trial_of_a(world)
        change_subscription(world, miss_the_payment)
        world.workshop.clock.advance(31 * DAY_SECONDS)
        world.tick("offboard_unpaid_businesses")
        assert closure_of_a(world)["state"] == "pending_deletion"

        change_subscription(world, pay)
        assert closure_of_a(world)["can_cancel"] is True
        world.tick("offboard_unpaid_businesses")

        assert closure_of_a(world)["state"] == "active"


def test_an_owner_cannot_cancel_a_closure_for_non_payment_without_paying() -> None:
    with open_closure_world() as world:
        start_trial_of_a(world)
        change_subscription(world, miss_the_payment)
        world.workshop.clock.advance(31 * DAY_SECONDS)
        world.tick("offboard_unpaid_businesses")
        owner = bearer(world.workshop.sign_in_with_phone(STRANGER_OWNER_PHONE)[0])

        refused = world.workshop.client.delete(
            f"/v1/businesses/{world.business_a}/closure", headers=owner
        )

        assert refused.status_code == 409
        assert "pay" in refused.json()["message"]


def test_a_business_that_never_paid_is_left_alone() -> None:
    with open_closure_world() as world:
        world.workshop.clock.advance(400 * DAY_SECONDS)

        world.tick("offboard_unpaid_businesses")

        assert closure_of_a(world)["state"] == "active"
