"""
Going live needs a running trial, a paid subscription or a trial still to
start at go-live, the DPA and a manager contact.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from tests.assembly.builders import make_launch_ready
from tests.assembly.international_business_seeds import seed_italian_restaurant
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

    with pytest.raises(ConflictError, match="Pay for the subscription"):
        testbed.publish(business.id, version.id)

    assert_nothing_went_live(testbed, business, version)
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)
    with pytest.raises(ConflictError, match="Pay for the subscription"):
        testbed.publish(business.id, version.id)

    subscription.status = SubscriptionStatus.CANCELLED
    subscription.period_end = Microseconds(
        int(testbed.wall_clock.now_unix()) + 3_600_000_000
    )
    testbed.subscription_repo.save(subscription)
    published = testbed.publish(business.id, version.id)  # paid until period end
    assert published.status is AssistantVersionStatus.PUBLISHED


def test_the_trial_starts_when_a_business_without_one_first_goes_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    version = ready_version(testbed, business)

    with pytest.raises(ConflictError) as refused:
        testbed.publish(business.id, version.id)

    message = str(refused.value)
    assert "Pay for the subscription" not in message
    assert "Accept the data processing agreement (version 2026-10-01)." in message
    assert "Add a staff contact" in message
    assert reason_codes(refused.value) == [
        ("dpa", ["2026-10-01"]),
        ("staff_contact", ["no_handoff_contact"]),
    ]
    assert_nothing_went_live(testbed, business, version)
    assert testbed.subscription_repo.list_by_business(business.id) == []

    make_launch_ready(testbed, testbed.business(business.id), with_trial=False)
    published = testbed.publish(business.id, version.id)

    assert published.status is AssistantVersionStatus.PUBLISHED
    trial = only_subscription(testbed, business)
    assert trial.status is SubscriptionStatus.TRIALING
    assert trial.trial_ends_at is not None
    assert int(trial.trial_ends_at) > int(testbed.wall_clock.now_unix())
    assert trial.period_start == testbed.wall_clock.now_unix()
    live = testbed.business(business.id)
    assert live.service_mode is ServiceMode.FULL
    assert live.plan_key == trial.plan_key
    kinds = [
        event.kind
        for event in testbed.activation_event_repo.list_by_business(business.id)
    ]
    assert kinds == [ActivationEventKind.WENT_LIVE]


def test_a_running_trial_is_not_restarted_at_go_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    before = only_subscription(testbed, business)
    version = ready_version(testbed, business)
    testbed.advance(3600)

    testbed.publish(business.id, version.id)

    after = only_subscription(testbed, business)
    assert after.id == before.id
    assert after.trial_ends_at == before.trial_ends_at
    assert after.period_start == before.period_start


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
