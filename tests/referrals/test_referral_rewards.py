"""An owner's invitation: a month of credit for both, after the first payment."""

from app.schemas.constants.billing import BillingCreditKind
from app.utilities.referrals.commission_math import commission_month
from tests.billing.paid_world import checkout, pay, payment_order
from tests.referrals.referral_billing_world import invited_trial


def test_the_reward_comes_only_after_the_first_payment() -> None:
    world = invited_trial()
    assert world.referring is not None

    session = checkout(world.paid)

    assert world.credits(world.business_id) == []
    assert world.credits(world.referring.id) == []
    assert world.referral().first_paid_at is None

    pay(world.paid, session)

    for business_id in (world.business_id, world.referring.id):
        credits = world.credits(business_id)
        assert len(credits) == 1
        assert credits[0].kind is BillingCreditKind.GRANTED
        assert credits[0].referral_of == world.business_id
        assert int(credits[0].amount_minor) > 0
        assert credits[0].currency_code == world.paid.business.currency_code

    referral = world.referral()
    assert referral.first_paid_at is not None
    assert referral.rewarded_at is not None


def test_a_month_is_granted_once_for_all_later_payments() -> None:
    world = invited_trial()
    assert world.referring is not None
    session = checkout(world.paid)
    pay(world.paid, session)
    first_rewarded_at = world.referral().rewarded_at

    world.paid.testbed.clock.advance(days=14, hours=1)
    world.paid.testbed.run_job(world.paid.testbed.end_trials, "end_trials")
    world.renew(payment_order(world.paid, session), payment_id=2)

    assert len(world.credits(world.business_id)) == 1
    assert len(world.credits(world.referring.id)) == 1
    assert world.referral().rewarded_at == first_rewarded_at


def test_a_repeated_payment_notice_grants_nothing_more() -> None:
    world = invited_trial()
    assert world.referring is not None
    session = checkout(world.paid)
    pay(world.paid, session)

    order = payment_order(world.paid, session)
    world.paid.testbed.deliver_flitt_callback(
        world.paid.testbed.callback_parameters(order, "approved", payment_id=1)
    )

    assert len(world.credits(world.business_id)) == 1
    assert len(world.credits(world.referring.id)) == 1


def test_a_declined_payment_rewards_nobody() -> None:
    world = invited_trial()
    assert world.referring is not None
    session = checkout(world.paid)
    order = payment_order(world.paid, session)

    world.paid.testbed.deliver_flitt_callback(
        world.paid.testbed.callback_parameters(order, "declined", payment_id=1)
    )

    assert world.credits(world.business_id) == []
    assert world.credits(world.referring.id) == []
    assert world.referral().first_paid_at is None


def test_an_invitation_earns_no_partner_commission() -> None:
    world = invited_trial()
    pay(world.paid, checkout(world.paid))

    month = commission_month(world.paid.testbed.clock.now())
    commissions = world.paid.testbed.referrals.commission_entry_repo
    assert commissions.totals_of_month(month) == []
