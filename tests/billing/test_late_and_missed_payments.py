"""Missed renewals, late payments and unpaid overage around the grace period."""

from typing import cast

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.utilities.billing.billing_periods import to_local_calendar_day
from tests.billing.billing_settings import ITALY
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.grace_steps import end_trial, enforce, pay_open_invoices, start_trial


def test_missed_renewal_becomes_past_due_after_a_day() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    period_end = testbed.subscription(business.id).period_end

    testbed.clock.move_to(period_end)
    testbed.clock.advance(hours=12)
    assert enforce(testbed) == 0

    testbed.clock.advance(hours=13)
    assert enforce(testbed) == 1

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    missed = testbed.invoices(business.id)[-1]
    assert missed.status is InvoiceStatus.ISSUED
    assert missed.period_start == period_end
    [(contact, text)] = testbed.notifier.sent
    assert contact.channel is ManagerContactChannel.EMAIL
    assert str(contact.name) == "Giulia"
    assert str(contact.language) == "it"
    assert str(text) == (
        "Trattoria: the payment of €175.00 for the new period has not arrived. "
        "Please pay in Billing. The assistant keeps full service until "
        "November 23, 2026; after that it will only take requests."
    )


def test_renewal_paid_ahead_moves_the_period_on_time() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed, ITALY)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    subscription = testbed.subscription(business.id)
    order = testbed.payment_order_repo.list_by_business(business.id)[0]
    testbed.clock.move_to(subscription.period_end)
    testbed.clock.advance(hours=-3)
    testbed.deliver_flitt_callback(
        testbed.callback_parameters(order, "approved", payment_id=2, amount=17500)
    )
    assert testbed.subscription(business.id).period_end == subscription.period_end

    testbed.clock.advance(hours=4)
    assert enforce(testbed) == 1

    moved = testbed.subscription(business.id)
    assert moved.status is SubscriptionStatus.ACTIVE
    assert moved.period_start == subscription.period_end
    assert testbed.notifier.sent == []


def test_paying_long_after_a_missed_renewal_buys_service_from_today() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    old_period_end = testbed.subscription(business.id).period_end
    testbed.clock.move_to(old_period_end)
    testbed.clock.advance(days=2)
    enforce(testbed)
    [stale] = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.status is InvoiceStatus.ISSUED
    ]
    testbed.clock.advance(days=8)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    testbed.clock.advance(days=63)

    pay_open_invoices(testbed, owner, business, payment_id=7)

    today = testbed.clock.now()
    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start <= today < subscription.period_end
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    stored_stale = testbed.invoice_repo.get(business.id, stale.id)
    assert stored_stale is not None
    assert stored_stale.status is InvoiceStatus.VOID
    recurring = cast(
        dict[str, object], testbed.flitt.checkout_orders[-1]["recurring_data"]
    )
    assert str(recurring["start_time"]) >= str(
        to_local_calendar_day(today, business.timezone)
    )
    assert enforce(testbed) == 0
    assert testbed.business(business.id).service_mode is ServiceMode.FULL


def test_paying_a_trial_long_after_it_ended_restores_full_service() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    testbed.clock.advance(days=40)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY

    pay_open_invoices(testbed, owner, business)

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.period_start <= testbed.clock.now() < subscription.period_end
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    paid = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.status is InvoiceStatus.PAID
    ]
    assert sorted(invoice.kind for invoice in paid) == [
        InvoiceKind.SERVICE_PERIOD,
        InvoiceKind.SETUP_FEE,
    ]


def test_a_cancelled_subscription_keeps_the_month_paid_ahead_in_the_trial() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    pay_open_invoices(testbed, owner, business)
    testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )
    [paid_month] = [
        invoice
        for invoice in testbed.invoices(business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    ]
    testbed.clock.advance(days=14, hours=1)

    end_trial(testbed)
    enforce(testbed)

    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    assert testbed.notifier.sent == []
    testbed.clock.move_to(paid_month.period_end)
    testbed.clock.advance(hours=-1)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.FULL

    testbed.clock.advance(hours=2)
    assert enforce(testbed) == 1
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY
    [(_, text)] = testbed.notifier.sent
    assert "Trattoria" in str(text)


def test_unpaid_overage_makes_the_subscription_past_due() -> None:
    testbed = BillingTestbed()
    owner, business = start_trial(testbed)
    pay_open_invoices(testbed, owner, business)
    testbed.clock.advance(days=14, hours=1)
    end_trial(testbed)
    period = testbed.subscription(business.id)
    testbed.record_usage(
        business.id,
        UsageKind.VOICE_SECONDS,
        500 * 60,
        occurred_at=period.period_start,
    )
    testbed.clock.move_to(period.period_end)
    testbed.clock.advance(hours=1)
    order = testbed.payment_order_repo.list_by_business(business.id)[0]
    testbed.deliver_flitt_callback(
        {
            **testbed.callback_parameters(
                order, "approved", payment_id=2, amount=51700
            ),
            "order_id": f"{order.id}_2",
            "parent_order_id": str(order.id),
        }
    )

    assert testbed.run_job(testbed.invoice_usage_overage, "invoice_usage_overage") == 1
    enforce(testbed)

    subscription = testbed.subscription(business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    testbed.clock.advance(days=7, hours=1)
    enforce(testbed)
    assert testbed.business(business.id).service_mode is ServiceMode.LEADS_ONLY

    pay_open_invoices(testbed, owner, business, payment_id=3)

    assert testbed.subscription(business.id).status is SubscriptionStatus.ACTIVE
    assert testbed.business(business.id).service_mode is ServiceMode.FULL
    assert testbed.flitt.stopped_orders == [str(order.id)]
    assert enforce(testbed) == 0
