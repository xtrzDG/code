"""
A new card at Stripe: saved through another Checkout that charges nothing
now, whose subscription takes over the charges (the earlier one is
cancelled). A charge Stripe declined is paid instead, which saves the card
paid with. A card replaced on the subscription at Stripe itself shows too.
"""

import pytest

from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentWebhookOutcome,
)
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.strings import PaymentProviderReference
from tests.billing.paid_world import PaidWorld, checkout, payment_order
from tests.billing.stripe_sandbox import MASTERCARD, STRIPE_CHECKOUT_URL
from tests.payments.payment_world import (
    MICROSECONDS_PER_SECOND,
    deliver_stripe,
    now_seconds,
    payment_method,
    save_card,
    setup_order,
    stripe_invoice,
    stripe_session,
)
from tests.payments.test_stripe_renewals import (
    build_stripe_subscription,
    decline_renewal,
)


def save_new_card(world: PaidWorld) -> PaymentOrderDocument:
    """
    "Update card": another Checkout that charges nothing now; Stripe starts
    a second subscription with the new card.
    """

    setup = setup_order(world)
    world.testbed.stripe.payment_method = MASTERCARD
    receipt = deliver_stripe(
        world,
        "checkout.session.completed",
        "evt_test_0020",
        {
            **stripe_session(setup, "no_payment_required", "sub_test_0002"),
            "customer": "cus_test_0002",
            "invoice": None,
        },
    )
    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    return setup


def test_a_new_card_is_saved_through_another_checkout() -> None:
    world, _ = build_stripe_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end

    setup = save_new_card(world)

    assert setup.provider is PaymentProvider.STRIPE
    assert setup.purpose is PaymentOrderPurpose.CARD_SETUP
    assert str(setup.checkout_url) == STRIPE_CHECKOUT_URL
    [_, form] = world.testbed.stripe.checkout_sessions
    assert form["mode"] == "subscription"
    assert form["payment_method_types[0]"] == "card"
    # Nothing is charged now: the plan price alone, from the paid period's end.
    assert "line_items[1][price_data][unit_amount]" not in form
    assert int(form["subscription_data[trial_end]"]) == (
        int(period_end) // MICROSECONDS_PER_SECOND
    )
    # The earlier Stripe subscription stops: only the new card is charged.
    assert world.testbed.stripe.cancelled_subscriptions == ["sub_test_0001"]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.provider_reference == PaymentProviderReference("sub_test_0002")
    summary = subscription.payment_method_summary
    assert summary is not None
    assert (str(summary.brand), str(summary.last_digits)) == ("MASTERCARD", "4444")
    assert payment_method(world).has_auto_debit


def test_the_new_cards_subscription_pays_the_next_period() -> None:
    world, order = build_stripe_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    setup = save_new_card(world)
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(hours=1)

    receipt = deliver_stripe(
        world,
        "invoice.paid",
        "evt_test_0021",
        stripe_invoice(setup, "in_test_0021", subscription_id="sub_test_0002"),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    renewal = world.testbed.invoices(world.business.id)[-1]
    assert renewal.status is InvoiceStatus.PAID
    assert renewal.period_start == period_end
    assert world.testbed.subscription(world.business.id).period_start == period_end

    # A charge of the earlier subscription that still came is owed back.
    late = deliver_stripe(
        world, "invoice.paid", "evt_test_0022", stripe_invoice(order, "in_test_0022")
    )

    assert late.outcome is PaymentWebhookOutcome.REFUND_DUE
    assert world.testbed.invoices(world.business.id)[-1].id == renewal.id


def test_a_card_replaced_at_stripe_itself_is_the_card_on_file() -> None:
    world, order = build_stripe_subscription()
    world.testbed.stripe.payment_method = MASTERCARD

    receipt = replace_card(world, order, "evt_test_0023")

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    summary = world.testbed.subscription(world.business.id).payment_method_summary
    assert summary is not None
    assert (str(summary.brand), str(summary.last_digits)) == ("MASTERCARD", "4444")


def replace_card(
    world: PaidWorld,
    order: PaymentOrderDocument,
    event_id: str,
    created: int | None = None,
) -> PaymentWebhookReceipt:
    return deliver_stripe(
        world,
        "customer.subscription.updated",
        event_id,
        {
            "id": "sub_test_0001",
            "customer": "cus_test_0001",
            "metadata": {"payment_order_id": str(order.id)},
            "default_payment_method": "pm_test_0002",
        },
        previous={"default_payment_method": "pm_test_0001"},
        created=created,
    )


def test_an_older_card_event_never_replaces_a_newer_card() -> None:
    world, order = build_stripe_subscription()
    world.testbed.stripe.payment_method = MASTERCARD

    replace_card(
        world, order, "evt_test_0021", created=now_seconds(world) - 15 * 86_400
    )

    summary = world.testbed.subscription(world.business.id).payment_method_summary
    assert summary is not None
    assert str(summary.last_digits) == "4242"


def test_a_subscription_update_without_a_new_card_changes_nothing() -> None:
    world, order = build_stripe_subscription()

    receipt = deliver_stripe(
        world,
        "customer.subscription.updated",
        "evt_test_0022",
        {"id": "sub_test_0001", "metadata": {"payment_order_id": str(order.id)}},
        previous={"status": "trialing"},
    )

    assert receipt.outcome is PaymentWebhookOutcome.IGNORED


def test_a_charge_stripe_declined_is_paid_instead_of_saving_a_card() -> None:
    world, order = build_stripe_subscription()
    failed = decline_renewal(world, order)
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )

    # The retries pay the invoice of the Stripe subscription that runs, with
    # its card: a card saved now would start another subscription instead.
    view = payment_method(world)
    assert not view.can_save_card
    assert view.retry is not None
    with pytest.raises(ConflictError):
        save_card(world)

    assert len(world.testbed.stripe.checkout_sessions) == 1

    paid = payment_order(world, checkout(world))
    assert failed.id in paid.invoice_ids
    world.testbed.stripe.payment_method = MASTERCARD
    receipt = deliver_stripe(
        world,
        "checkout.session.completed",
        "evt_test_0200",
        {**stripe_session(paid, "paid", "sub_test_0002"), "customer": "cus_test_0002"},
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    assert world.testbed.stripe.cancelled_subscriptions == ["sub_test_0001"]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.provider_reference == PaymentProviderReference("sub_test_0002")
    summary = subscription.payment_method_summary
    assert summary is not None
    assert str(summary.last_digits) == "4444"
    assert payment_method(world).can_save_card
