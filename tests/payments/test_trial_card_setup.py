"""A card saved in the trial: verified for nothing, charged when the trial ends."""

from app.schemas.constants.billing import (
    InvoiceStatus,
    SetupOption,
    SubscriptionStatus,
)
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentStatus,
    PaymentWebhookOutcome,
)
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_settings import CHECKOUT_URL
from tests.billing.paid_world import build_trial
from tests.payments.payment_world import (
    confirm_card,
    payment_method,
    reload,
    save_card,
    setup_order,
)


def test_saving_a_card_in_the_trial_verifies_it_for_nothing() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)
    trial_ends_at = world.testbed.subscription(world.business.id).trial_ends_at
    assert trial_ends_at is not None

    session = save_card(world)

    assert session.provider is PaymentProvider.FLITT
    assert str(session.url) == CHECKOUT_URL
    sent = world.testbed.flitt.checkout_orders[-1]
    assert (sent["amount"], sent["verification"], sent["verification_type"]) == (
        0,
        "Y",
        "amount",
    )
    assert sent["required_rectoken"] == "Y"
    order = setup_order(world)
    recurring = sent["recurring_data"]
    assert isinstance(recurring, dict)
    assert recurring["amount"] == int(order.recurring_amount_minor) > 0
    assert recurring["start_time"] == str(
        to_local_calendar_day(trial_ends_at, world.business.timezone)
    )
    assert order.purpose is PaymentOrderPurpose.CARD_SETUP
    assert order.invoice_ids == []
    assert world.testbed.invoices(world.business.id) == []


def test_a_verified_card_runs_the_charges_from_the_trial_end() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)
    order = setup_order(world)

    assert confirm_card(world, order) is PaymentWebhookOutcome.APPLIED

    stored = reload(world, order)
    assert stored.is_initial_payment_settled
    assert stored.status is PaymentStatus.APPROVED
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert subscription.provider_reference == PaymentProviderReference(str(order.id))
    assert world.testbed.invoices(world.business.id) == []
    view = payment_method(world)
    assert view.has_auto_debit
    assert view.card is not None
    assert str(view.card.last_digits) == "1111"
    assert not view.is_trial_card_prompt_due


def test_the_trial_end_waits_for_the_saved_card_and_its_charge_pays() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)
    order = setup_order(world)
    confirm_card(world, order)
    world.testbed.clock.advance(days=14, hours=1)

    assert world.testbed.run_job(world.testbed.end_trials, "end_trials") == 0
    assert world.testbed.invoices(world.business.id) == []

    receipt = world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "approved",
                payment_id=8,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": f"{order.id}_1",
            "parent_order_id": str(order.id),
        }
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    [first] = world.testbed.invoices(world.business.id)
    assert first.status is InvoiceStatus.PAID
    assert first.period_start == subscription.period_start


def test_a_declined_first_charge_after_the_trial_starts_the_grace() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)
    order = setup_order(world)
    confirm_card(world, order)
    world.testbed.clock.advance(days=14, hours=1)

    world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "declined",
                payment_id=9,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": f"{order.id}_1",
            "parent_order_id": str(order.id),
        }
    )

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert subscription.grace_until is not None
    [failed] = world.testbed.invoices(world.business.id)
    assert failed.status is InvoiceStatus.FAILED
    assert len(world.testbed.notifier.sent) == 1


def test_a_trial_with_no_card_charge_ends_as_before_a_day_later() -> None:
    world = build_trial(setup_option=SetupOption.SELF_SERVE)
    confirm_card(world, setup_order(world))
    world.testbed.clock.advance(days=15, hours=2)

    assert world.testbed.run_job(world.testbed.end_trials, "end_trials") == 1

    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )
