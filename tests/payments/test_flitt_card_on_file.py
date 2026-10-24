"""The card Flitt saves: its summary, its sealed token, and saving a new one."""

import pytest

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.payments import (
    PaymentProvider,
    PaymentWebhookOutcome,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.exceptions.application_errors import AccessDeniedError, ConflictError
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.paid_world import (
    PaidWorld,
    build_active_subscription,
    build_trial,
    checkout,
    pay,
    payment_order,
)
from tests.payments.payment_world import (
    CARD_TOKEN,
    card_callback,
    confirm_card,
    flitt_pay_with_card,
    payment_method,
    reload,
    save_card,
    setup_order,
)


def test_the_first_payment_keeps_the_card_flitt_saved() -> None:
    world = build_trial()
    order = flitt_pay_with_card(world)

    assert world.testbed.flitt.checkout_orders[-1]["required_rectoken"] == "Y"
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.payment_provider is PaymentProvider.FLITT
    assert subscription.provider_reference == PaymentProviderReference(str(order.id))
    summary = subscription.payment_method_summary
    assert summary is not None
    assert summary.provider is PaymentProvider.FLITT
    assert (str(summary.brand), str(summary.last_digits)) == ("VISA", "1111")
    assert (int(summary.expiry_month or 0), int(summary.expiry_year or 0)) == (9, 2029)
    assert summary.saved_at == world.testbed.clock.now()
    assert order.sealed_card_token is not None
    assert CARD_TOKEN not in str(order.sealed_card_token)
    assert str(world.testbed.secret_cipher.decrypt(order.sealed_card_token)) == (
        CARD_TOKEN
    )


def test_a_repeated_callback_saves_the_card_once() -> None:
    world = build_trial()
    order = flitt_pay_with_card(world)
    sealed = order.sealed_card_token
    world.testbed.clock.advance(hours=1)

    receipt = world.testbed.deliver_flitt_callback(
        card_callback(world, order, "approved", 1)
    )

    assert receipt.outcome is PaymentWebhookOutcome.DUPLICATE
    assert reload(world, order).sealed_card_token == sealed
    summary = world.testbed.subscription(world.business.id).payment_method_summary
    assert summary is not None
    assert summary.saved_at < world.testbed.clock.now()


def test_no_card_is_kept_without_a_token_or_an_approval() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    world.testbed.deliver_flitt_callback(card_callback(world, order, "declined", 1))
    pay(world, session, payment_id=2)

    assert reload(world, order).sealed_card_token is None
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.payment_method_summary is None
    assert subscription.provider_reference is not None


def test_updating_the_card_replaces_the_running_charges() -> None:
    world, first_order = build_active_subscription()
    world.testbed.clock.advance(days=3)
    order = setup_order(world)
    period_end = world.testbed.subscription(world.business.id).period_end
    sent = world.testbed.flitt.checkout_orders[-1]
    recurring = sent["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["start_time"] == str(
        to_local_calendar_day(period_end, world.business.timezone)
    )

    assert (
        confirm_card(
            world, order, masked_card="535555XXXXXX4444", card_type="MASTERCARD"
        )
        is PaymentWebhookOutcome.APPLIED
    )

    assert world.testbed.flitt.stopped_orders == [str(first_order.id)]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.provider_reference == PaymentProviderReference(str(order.id))
    summary = subscription.payment_method_summary
    assert summary is not None
    assert (str(summary.brand), str(summary.last_digits)) == ("MASTERCARD", "4444")


def test_a_card_of_replaced_charges_never_becomes_the_card_on_file() -> None:
    world = build_trial()
    first = flitt_pay_with_card(world)
    second = setup_order(world)
    confirm_card(world, second, masked_card="XXXX1234")
    world.testbed.clock.advance(hours=1)

    receipt = world.testbed.deliver_flitt_callback(
        card_callback(
            world,
            first,
            "approved",
            3,
            amount=int(first.recurring_amount_minor),
            masked_card="X9999",
        )
    )

    assert receipt.outcome is PaymentWebhookOutcome.REFUND_DUE
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.provider_reference == PaymentProviderReference(str(second.id))
    summary = subscription.payment_method_summary
    assert summary is not None
    assert str(summary.last_digits) == "1234"


def test_a_card_cannot_be_saved_over_an_unpaid_bill() -> None:
    world = build_trial()
    checkout(world)
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")

    with pytest.raises(ConflictError):
        save_card(world)

    assert not payment_method(world).can_save_card


def test_only_owners_see_and_save_the_card() -> None:
    world = build_trial()
    staff = world.testbed.add_user(email="staff@example.com")
    business = world.testbed.business(world.business.id)
    business.members.append(
        BusinessMember(user_id=staff.id, role=BusinessMemberRole.STAFF)
    )
    world.testbed.business_repo.save(business)
    as_staff = PaidWorld(testbed=world.testbed, owner=staff, business=business)

    with pytest.raises(AccessDeniedError):
        payment_method(as_staff)

    with pytest.raises(AccessDeniedError):
        save_card(as_staff)

    assert world.testbed.flitt.checkout_orders == []
