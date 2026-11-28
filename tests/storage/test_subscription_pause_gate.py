"""
The pause's release gate is open from this release: the release before it
(launch-2026-11-05) reads a paused subscription, so this one offers and
stores the status once SUBSCRIPTION_PAUSE_ENABLED is on
(docs/operations/deploys.md).
"""

from app.schemas.constants.billing import SubscriptionStatus
from app.utilities.storage.release_gates import SUBSCRIPTION_PAUSE_GATE, is_gate_open
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld


def test_the_pause_is_offered_once_turned_on() -> None:
    world = LifecycleWorld(is_pause_enabled=True)
    _, business = world.paying_business()

    pause = world.lifecycle_of(business).pause

    assert is_gate_open(SUBSCRIPTION_PAUSE_GATE) is True
    assert pause.is_enabled is True
    assert pause.unavailable_reason is None


def test_storage_keeps_a_paused_subscription_now_its_gate_is_open() -> None:
    world = LifecycleWorld(is_pause_enabled=True)
    _, business = world.paying_business()
    subscription = world.current(business)
    subscription.status = SubscriptionStatus.PAUSED

    world.subscription_repo.save(subscription)

    assert world.current(business).status is SubscriptionStatus.PAUSED
