"""The card on file as the billing page shows it, and who charges it."""

import pytest

from app.schemas.constants.billing import SetupOption
from app.schemas.constants.payments import PaymentProvider, PaymentRetryOutcome
from app.schemas.dto.payment_methods import PaymentMethodQuery
from app.utilities.billing.billing_periods import add_local_days
from tests.billing.billing_settings import (
    GEORGIA,
    ISRAEL,
    ITALY,
    JAPAN,
    KAZAKHSTAN,
    USA,
    CountryPreset,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.paid_world import build_trial
from tests.payments.payment_world import (
    CARD_FIELDS,
    flitt_pay_with_card,
    payment_method,
    save_card,
)
from tests.payments.test_dunning_retries import build_declined_charge, run_dunning


def test_a_new_trial_shows_no_card_and_no_prompt_yet() -> None:
    world = build_trial()

    view = payment_method(world)

    assert view.provider is PaymentProvider.FLITT
    assert view.card is None
    assert not view.has_auto_debit
    assert view.can_save_card
    assert (
        view.trial_ends_at
        == world.testbed.subscription(world.business.id).trial_ends_at
    )
    assert not view.is_trial_card_prompt_due
    assert view.retry is None


def test_the_trial_asks_for_a_card_from_day_ten() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)
    subscription = world.testbed.subscription(world.business.id)
    day_ten = add_local_days(subscription.period_start, 9, world.business.timezone)
    world.testbed.clock.move_to(day_ten)
    world.testbed.clock.advance(hours=-1)

    assert not payment_method(world).is_trial_card_prompt_due

    world.testbed.clock.advance(hours=1)

    assert payment_method(world).is_trial_card_prompt_due

    session = save_card(world)
    order = world.testbed.payment_order_repo.get(session.payment_order_id)  # type: ignore[arg-type]
    assert order is not None
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            order, "approved", payment_id=4, amount=0, **CARD_FIELDS
        )
    )

    view = payment_method(world)
    assert not view.is_trial_card_prompt_due
    assert view.card is not None
    assert view.card.expiry_month is not None
    assert (int(view.card.expiry_month), int(view.card.expiry_year or 0)) == (
        9,
        2029,
    )


def test_a_trial_paid_ahead_with_a_card_is_never_prompted() -> None:
    world = build_trial()
    flitt_pay_with_card(world)
    world.testbed.clock.advance(days=12)

    view = payment_method(world)

    assert view.has_auto_debit
    assert not view.is_trial_card_prompt_due


@pytest.mark.parametrize(
    ("country", "provider"),
    [
        (GEORGIA, PaymentProvider.FLITT),
        (ITALY, PaymentProvider.STRIPE),
        (USA, PaymentProvider.STRIPE),
        (ISRAEL, PaymentProvider.STRIPE),
        (JAPAN, PaymentProvider.FLITT),
        (KAZAKHSTAN, PaymentProvider.FLITT),
    ],
)
@pytest.mark.usefixtures("stripe_gate_open")
def test_the_region_names_the_provider(
    country: CountryPreset, provider: PaymentProvider
) -> None:
    assert payment_method(build_trial(country)).provider is provider


def test_until_the_release_gate_opens_everyone_pays_through_flitt() -> None:
    world = build_trial(ITALY)

    assert payment_method(world).provider is PaymentProvider.FLITT
    assert save_card(world).provider is PaymentProvider.FLITT


def test_the_retries_of_a_declined_charge_are_shown() -> None:
    world, _, _ = build_declined_charge()
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.grace_until is not None
    grace_start = add_local_days(subscription.grace_until, -7, world.business.timezone)

    before = payment_method(world).retry
    world.testbed.flitt.recurring_status = "declined"
    world.testbed.clock.advance(hours=25)
    run_dunning(world)
    after = payment_method(world).retry

    assert before is not None
    assert before.last_attempt is None
    assert before.next_retry_at == add_local_days(
        grace_start, 1, world.business.timezone
    )
    assert before.grace_until == subscription.grace_until
    assert after is not None
    assert after.last_attempt is not None
    assert int(after.last_attempt) == 1
    assert after.last_outcome is PaymentRetryOutcome.DECLINED
    assert after.next_retry_at == add_local_days(
        grace_start, 3, world.business.timezone
    )
    # A declined charge being retried: the card may be replaced meanwhile.
    assert payment_method(world).can_save_card


def test_a_business_without_a_subscription_has_no_card_to_save() -> None:
    testbed = BillingTestbed()
    owner = testbed.add_user(email="owner@example.com")
    business = testbed.add_business(owner, USA)

    view = testbed.payments.get_payment_method.run(
        PaymentMethodQuery(user_id=owner.id, business_id=business.id)
    )

    assert view.card is None
    assert not view.can_save_card
    assert view.trial_ends_at is None
    assert view.retry is None
