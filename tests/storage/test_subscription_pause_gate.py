"""
This release reads a paused subscription but neither stores nor offers the
status: its release gate opens in the next release, whatever
SUBSCRIPTION_PAUSE_ENABLED says (docs/operations/deploys.md).
"""

import pytest

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.subscription_lifecycle import PauseUnavailableReason
from app.schemas.exceptions.storage_errors import ClosedReleaseGateError
from app.utilities.storage.release_gates import SUBSCRIPTION_PAUSE_GATE, is_gate_open
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld


def test_the_pause_waits_for_the_next_release_even_when_turned_on() -> None:
    world = LifecycleWorld(is_pause_enabled=True)
    _, business = world.paying_business()

    pause = world.lifecycle_of(business).pause

    assert is_gate_open(SUBSCRIPTION_PAUSE_GATE) is False
    assert pause.is_enabled is False
    assert pause.unavailable_reason is PauseUnavailableReason.FEATURE_OFF


def test_storage_refuses_a_paused_subscription_until_the_gate_opens() -> None:
    world = LifecycleWorld(is_pause_enabled=True)
    _, business = world.paying_business()
    subscription = world.current(business)
    subscription.status = SubscriptionStatus.PAUSED

    with pytest.raises(ClosedReleaseGateError, match="paused"):
        world.subscription_repo.save(subscription)
    assert world.current(business).status is SubscriptionStatus.ACTIVE
