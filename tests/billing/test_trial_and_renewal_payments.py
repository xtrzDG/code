"""Payments around the trial's end and automatic monthly renewals."""

import pytest

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.exceptions.application_errors import ConflictError
from tests.billing.paid_world import (
    build_active_subscription,
    build_trial,
    checkout,
    pay,
    payment_order,
)


def test_trial_paid_ahead_becomes_active_when_it_ends() -> None:
    world, order = build_active_subscription()

    subscription = world.testbed.subscription(world.business.id)
    period_invoice = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    ][0]
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == period_invoice.period_start
    assert subscription.period_end == period_invoice.period_end
    assert subscription.grace_until is None
    assert str(subscription.provider_reference) == str(order.id)
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL


def test_payment_after_the_trial_activates_at_once() -> None:
    world = build_trial()
    world.testbed.clock.advance(days=20)
    session = checkout(world)

    pay(world, session)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == world.testbed.clock.now()
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL


def test_declined_first_payment_keeps_the_trial_and_tells_the_owner() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            order,
            "declined",
            response_description="Card expired",
        )
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    assert all(
        invoice.status is InvoiceStatus.FAILED
        for invoice in world.testbed.invoices(world.business.id)
    )
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.TRIALING
    )
    stored = payment_order(world, session)
    assert stored.status is PaymentStatus.DECLINED
    assert str(stored.last_failure_reason) == "Card expired"
    [(contact, text)] = world.testbed.notifier.sent
    assert contact.channel is ManagerContactChannel.WHATSAPP
    assert str(contact.address) == "+995599123456"
    assert str(contact.language) == "ka"
    assert "960,00\xa0₾" in str(text)

    retry = checkout(world)

    assert set(retry.invoice_ids) == set(session.invoice_ids)
    assert retry.payment_order_id != session.payment_order_id


def test_automatic_renewal_extends_the_subscription() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(hours=2)

    receipt = world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                "approved",
                payment_id=2,
                amount=51700,
            ),
            "order_id": f"{order.id}_2",
            "parent_order_id": str(order.id),
        }
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == period_end
    renewal = world.testbed.invoices(world.business.id)[-1]
    assert renewal.status is InvoiceStatus.PAID
    assert renewal.period_start == period_end
    assert str(renewal.provider_reference) == "2"


def test_declined_renewal_starts_the_grace_period() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)

    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "declined", payment_id=3, amount=51700)
    )

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert subscription.grace_until is not None
    assert int(subscription.grace_until) - int(world.testbed.clock.now()) == (
        7 * 24 * 60 * 60 * 1_000_000
    )
    failed = world.testbed.invoices(world.business.id)[-1]
    assert failed.status is InvoiceStatus.FAILED
    assert failed.period_start == period_end
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL
    [(_, text)] = world.testbed.notifier.sent
    assert "517,00\xa0₾" in str(text)
    assert "ამ თარიღამდე" in str(text)


def test_late_retry_pays_the_bill_of_the_missed_renewal() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(days=2)
    world.testbed.run_job(world.testbed.enforce_grace_periods, "enforce_grace_periods")
    invoice_count = len(world.testbed.invoices(world.business.id))

    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=4, amount=51700)
    )

    invoices = world.testbed.invoices(world.business.id)
    assert len(invoices) == invoice_count
    assert invoices[-1].period_start == period_end
    assert invoices[-1].status is InvoiceStatus.PAID
    assert str(invoices[-1].provider_reference) == "4"
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start == period_end
    assert subscription.grace_until is None


def test_a_renewal_is_billed_once_even_when_its_record_is_lost() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    declined = world.testbed.callback_parameters(
        order, "declined", payment_id=5, amount=51700
    )
    world.testbed.deliver_flitt_callback(declined)
    stored = world.testbed.payment_order_repo.get(order.id)
    assert stored is not None
    stored.processed_notification_keys.clear()
    world.testbed.payment_order_repo.save(stored)
    invoice_count = len(world.testbed.invoices(world.business.id))

    world.testbed.deliver_flitt_callback(declined)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved", payment_id=5, amount=51700)
    )

    invoices = world.testbed.invoices(world.business.id)
    assert len(invoices) == invoice_count
    assert invoices[-1].status is InvoiceStatus.PAID
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )


def test_a_trial_paid_ahead_is_never_billed_again() -> None:
    world = build_trial()
    pay(world, checkout(world))

    with pytest.raises(ConflictError):
        checkout(world)

    assert len(world.testbed.flitt.checkout_orders) == 1
    assert all(
        invoice.status is InvoiceStatus.PAID
        for invoice in world.testbed.invoices(world.business.id)
    )


def test_paying_after_cancelling_in_the_trial_resumes_it() -> None:
    world = build_trial()
    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    pay(world, checkout(world))

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    world.testbed.run_job(world.testbed.enforce_grace_periods, "enforce_grace_periods")
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL
