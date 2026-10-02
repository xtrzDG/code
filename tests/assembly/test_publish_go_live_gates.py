"""Going live needs a trial or paid subscription, the DPA and a manager contact."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.exceptions.application_errors import (
    ConflictError,
)
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from tests.assembly.builders import make_launch_ready
from tests.assembly.international_business_seeds import (
    seed_italian_restaurant,
)
from tests.assembly.publish_helpers import (
    assert_nothing_went_live,
    only_subscription,
    ready_version,
    reason_codes,
)
from tests.assembly.testbed import AssemblyTestbed


def test_going_live_needs_a_running_trial_or_a_paid_subscription() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    subscription = only_subscription(testbed, business)
    version = ready_version(testbed, business)
    trial_end = subscription.trial_ends_at
    assert trial_end is not None
    subscription.trial_ends_at = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)

    with pytest.raises(ConflictError, match="Start the trial or pay"):
        testbed.publish(business.id, version.id)

    assert_nothing_went_live(testbed, business, version)
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)
    with pytest.raises(ConflictError, match="Start the trial or pay"):
        testbed.publish(business.id, version.id)

    subscription.status = SubscriptionStatus.CANCELLED
    subscription.period_end = Microseconds(
        int(testbed.wall_clock.now_unix()) + 3_600_000_000
    )
    testbed.subscription_repo.save(subscription)
    published = testbed.publish(business.id, version.id)  # paid until period end
    assert published.status is AssistantVersionStatus.PUBLISHED


def test_a_business_that_never_started_the_trial_cannot_go_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    version = ready_version(testbed, business)

    with pytest.raises(ConflictError) as refused:
        testbed.publish(business.id, version.id)

    message = str(refused.value)
    assert "Start the trial or pay for the subscription." in message
    assert "Accept the data processing agreement (version 2026-10-01)." in message
    assert "Add a staff contact" in message
    assert reason_codes(refused.value) == [
        ("subscription_or_trial", ["none"]),
        ("dpa", ["2026-10-01"]),
        ("staff_contact", ["no_handoff_contact"]),
    ]
    assert_nothing_went_live(testbed, business, version)
    make_launch_ready(testbed, business)
    published = testbed.publish(business.id, version.id)
    assert published.status is AssistantVersionStatus.PUBLISHED


def test_going_live_needs_the_current_dpa() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)
    for acceptance in testbed.dpa_repo.list_by_business(business.id):
        acceptance.document_version = DpaDocumentVersion("2025-01-01")
        testbed.dpa_repo.save(acceptance)

    with pytest.raises(ConflictError, match="data processing agreement"):
        testbed.publish(business.id, version.id)

    assert_nothing_went_live(testbed, business, version)


def test_going_live_needs_a_manager_contact_and_no_blocking_gap() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = ready_version(testbed, business)
    stored = testbed.business(business.id)
    stored.manager_contacts = []
    testbed.business_repo.save(stored)
    profile = testbed.profile_repo.get_by_business(business.id)
    assert profile is not None
    profile.hours = []
    testbed.profile_repo.save(profile)

    with pytest.raises(
        ConflictError,
        match=r"Complete the profile \(see what to add: no_opening_hours\)\. "
        r"Add a staff contact who receives handoffs, bookings and leads\.",
    ) as refused:
        testbed.publish(business.id, version.id)

    assert reason_codes(refused.value) == [
        ("profile_gaps", ["no_opening_hours"]),
        ("staff_contact", ["no_handoff_contact"]),
    ]
    assert_nothing_went_live(testbed, business, version)
