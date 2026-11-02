"""
A number costs money every month and brings calls and text-backs, so only
a business that pays, or has a card on file in its trial or in the grace
of a missed payment, rents one (ABUSE-05). Everyone else is told to add a
card, and the carrier is never asked.
"""

import pytest

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import StartTrialCommand, StartTrialRequest
from app.schemas.exceptions.phone_number_errors import PhoneNumberNeedsPaymentError
from app.use_cases.shared.billing_records import find_current_subscription
from tests.phone_numbers.phone_world import PhoneWorld

GRACE_ENDED_DAYS: int = 60


def trial_without_card(world: PhoneWorld) -> tuple[UserDocument, BusinessDocument]:
    owner, business = world.owner_and_business(card_on_file=False)
    world.start_trial.run(
        StartTrialCommand(
            user_id=owner.id, business_id=business.id, request=StartTrialRequest()
        )
    )
    return owner, business


def set_status(
    world: PhoneWorld, business: BusinessDocument, status: SubscriptionStatus
) -> None:
    subscription = find_current_subscription(world.subscription_repo, business.id)
    assert subscription is not None
    subscription.status = status
    world.subscription_repo.save(subscription)


def assert_refused(
    world: PhoneWorld, owner: UserDocument, business: BusinessDocument
) -> None:
    with pytest.raises(PhoneNumberNeedsPaymentError) as refusal:
        world.rent_austin_number(owner, business)

    assert [str(reason.code) for reason in refusal.value.reasons] == [
        "payment_method_required"
    ]
    assert world.provisioner.bought == []
    assert world.phone_number_repo.find_held(business.id) is None


def test_a_business_without_a_subscription_rents_no_number() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business(card_on_file=False)

    assert_refused(world, owner, business)


def test_a_trial_without_a_card_rents_no_number() -> None:
    world = PhoneWorld()
    owner, business = trial_without_card(world)

    assert_refused(world, owner, business)


def test_the_card_saved_in_the_trial_lets_the_owner_take_one() -> None:
    world = PhoneWorld()
    owner, business = trial_without_card(world)
    assert_refused(world, owner, business)

    world.save_card(business)
    world.rent_austin_number(owner, business)

    assert len(world.provisioner.bought) == 1


def test_a_paying_business_rents_one() -> None:
    world = PhoneWorld()
    owner, business = trial_without_card(world)
    set_status(world, business, SubscriptionStatus.ACTIVE)

    world.rent_austin_number(owner, business)

    assert len(world.provisioner.bought) == 1


@pytest.mark.parametrize(
    "status", [SubscriptionStatus.INCOMPLETE, SubscriptionStatus.CANCELLED]
)
def test_an_unpaid_or_cancelled_plan_rents_none_even_with_a_card(
    status: SubscriptionStatus,
) -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    set_status(world, business, status)

    assert_refused(world, owner, business)


def test_a_missed_payment_past_its_grace_rents_none() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    subscription = find_current_subscription(world.subscription_repo, business.id)
    assert subscription is not None
    subscription.status = SubscriptionStatus.PAST_DUE
    subscription.grace_until = subscription.trial_ends_at
    world.subscription_repo.save(subscription)
    world.clock.advance(days=GRACE_ENDED_DAYS)

    assert_refused(world, owner, business)
