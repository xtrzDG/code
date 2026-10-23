"""
Saved card tokens are forgotten once their charges stop, and a card can be
replaced while a declined charge is retried: the retries charge the new one.
"""

from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.payments import PaymentOrderPurpose, PaymentWebhookOutcome
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.paid_world import build_trial
from tests.payments.payment_world import (
    confirm_card,
    flitt_pay_with_card,
    payment_method,
    reload,
    setup_order,
)
from tests.payments.test_dunning_retries import (
    DAY_HOURS,
    build_declined_charge,
    retries,
    run_dunning,
)

NEW_CARD_TOKEN: str = "rectoken-test-0001"


def test_cancelling_forgets_the_saved_card_token() -> None:
    world = build_trial()
    order = flitt_pay_with_card(world)
    assert order.sealed_card_token is not None

    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    assert reload(world, order).sealed_card_token is None
    assert world.testbed.subscription(world.business.id).payment_method_summary is None


def test_a_new_card_forgets_the_old_token_and_keeps_its_own() -> None:
    world = build_trial()
    first = flitt_pay_with_card(world)
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    replacement = setup_order(world)

    assert confirm_card(world, replacement, rectoken=NEW_CARD_TOKEN) is (
        PaymentWebhookOutcome.APPLIED
    )

    assert reload(world, first).sealed_card_token is None
    kept = reload(world, replacement).sealed_card_token
    assert kept is not None
    assert str(world.testbed.secret_cipher.decrypt(kept)) == NEW_CARD_TOKEN


def test_the_card_is_replaced_while_a_declined_charge_is_retried() -> None:
    world, old_order, invoice = build_declined_charge()
    assert payment_method(world).can_save_card

    replacement = setup_order(world)

    assert replacement.purpose is PaymentOrderPurpose.CARD_SETUP
    sent = world.testbed.flitt.checkout_orders[-1]
    recurring = sent["recurring_data"]
    assert isinstance(recurring, dict)
    # The new card's charges start after the declined period: the retries
    # pay that one, so it is never charged twice.
    assert recurring["start_time"] == str(
        to_local_calendar_day(invoice.period_end, world.business.timezone)
    )
    assert confirm_card(world, replacement, rectoken=NEW_CARD_TOKEN) is (
        PaymentWebhookOutcome.APPLIED
    )
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert subscription.provider_reference == PaymentProviderReference(
        str(replacement.id)
    )
    assert reload(world, old_order).sealed_card_token is None
    assert str(old_order.id) in world.testbed.flitt.stopped_orders

    world.testbed.clock.advance(hours=DAY_HOURS)
    assert run_dunning(world) == 1

    [charge] = world.testbed.flitt.recurring_orders
    assert charge["rectoken"] == NEW_CARD_TOKEN
    assert charge["merchant_data"] == str(replacement.id)
    [retry] = retries(world, invoice)
    settled = world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                reload(world, replacement),
                "approved",
                payment_id=81,
                amount=int(replacement.recurring_amount_minor),
            ),
            "order_id": str(retry.id),
        }
    )
    assert settled.outcome is PaymentWebhookOutcome.APPLIED
    [paid] = [
        stored
        for stored in world.testbed.invoices(world.business.id)
        if stored.id == invoice.id
    ]
    assert paid.status is InvoiceStatus.PAID
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
