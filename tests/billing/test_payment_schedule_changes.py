"""Plan changes, cancellations and new checkouts versus automatic charges."""

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.billing_cabinet import (
    CancelSubscriptionCommand,
    ChangePlanCommand,
    ChangePlanRequest,
)
from tests.billing.paid_world import (
    build_active_subscription,
    build_trial,
    checkout,
    pay,
    payment_order,
)


def test_plan_change_stops_automatic_charges_at_the_old_price() -> None:
    world, order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end

    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.PLUS,
                billing_period=BillingPeriod.MONTHLY,
            ),
        )
    )
    session = checkout(world)

    assert world.testbed.flitt.stopped_orders == [str(order.id)]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.provider_reference is None
    assert int(subscription.price_minor) == 103100
    next_invoice = world.testbed.invoices(world.business.id)[-1]
    assert next_invoice.period_start == period_end
    assert int(next_invoice.amount_minor) == 103100
    assert session.invoice_ids == [next_invoice.id]


def test_plan_change_voids_bills_at_the_old_price() -> None:
    world = build_trial()
    checkout(world)

    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.VOICE_AND_CHAT,
                billing_period=BillingPeriod.ANNUAL,
            ),
        )
    )

    assert [
        invoice.status for invoice in world.testbed.invoices(world.business.id)
    ] == [InvoiceStatus.VOID, InvoiceStatus.VOID]
    session = checkout(world)
    [annual] = [
        invoice
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.status is InvoiceStatus.ISSUED
    ]
    assert int(annual.amount_minor) == 527340
    assert session.invoice_ids == [annual.id]


def test_cancel_stops_automatic_charges() -> None:
    world, order = build_active_subscription()

    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    assert world.testbed.flitt.stopped_orders == [str(order.id)]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.CANCELLED
    assert subscription.provider_reference is None


def test_cancel_voids_unpaid_bills() -> None:
    world = build_trial()
    checkout(world)

    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    assert {
        invoice.status for invoice in world.testbed.invoices(world.business.id)
    } == {InvoiceStatus.VOID}
    assert world.testbed.flitt.stopped_orders == []


def test_a_decline_after_a_plan_change_leaves_voided_bills_alone() -> None:
    world = build_trial()
    session = checkout(world)
    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.CHAT,
                billing_period=BillingPeriod.MONTHLY,
            ),
        )
    )

    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(payment_order(world, session), "declined")
    )

    statuses = [invoice.status for invoice in world.testbed.invoices(world.business.id)]
    assert statuses == [InvoiceStatus.FAILED, InvoiceStatus.VOID]


def test_paying_with_a_new_checkout_stops_the_previous_schedule() -> None:
    world, first_order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            first_order, "declined", payment_id=3, amount=51700
        )
    )
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.PAST_DUE
    )

    retry = checkout(world)
    pay(world, retry, payment_id=4)

    assert world.testbed.flitt.stopped_orders == [str(first_order.id)]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert str(subscription.provider_reference) == str(retry.payment_order_id)


def test_charges_of_a_replaced_schedule_are_refunded_not_booked() -> None:
    world, first_order = build_active_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            first_order, "declined", payment_id=3, amount=51700
        )
    )
    retry = checkout(world)
    pay(world, retry, payment_id=4)
    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )
    invoice_count = len(world.testbed.invoices(world.business.id))
    world.testbed.clock.advance(days=31)

    receipt = world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                first_order, "approved", payment_id=5, amount=51700
            ),
            "order_id": f"{first_order.id}_5",
            "parent_order_id": str(first_order.id),
        }
    )

    assert receipt.outcome is PaymentWebhookOutcome.REFUND_DUE
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.CANCELLED
    assert len(world.testbed.invoices(world.business.id)) == invoice_count
    stored = world.testbed.payment_order_repo.get(first_order.id)
    assert stored is not None
    assert stored.is_refund_due
    assert world.testbed.flitt.stopped_orders == [
        str(first_order.id),
        str(retry.payment_order_id),
        str(first_order.id),
    ]
    assert world.testbed.business(world.business.id).service_mode is ServiceMode.FULL


def test_a_declined_charge_of_a_replaced_schedule_changes_nothing() -> None:
    world, first_order = build_active_subscription()
    world.testbed.change_plan.run(
        ChangePlanCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=ChangePlanRequest(
                plan_key=PlanKey.PLUS,
                billing_period=BillingPeriod.MONTHLY,
            ),
        )
    )
    world.testbed.clock.move_to(
        world.testbed.subscription(world.business.id).period_end
    )
    invoice_count = len(world.testbed.invoices(world.business.id))

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            first_order, "declined", payment_id=6, amount=51700
        )
    )

    assert receipt.outcome is PaymentWebhookOutcome.IGNORED
    assert len(world.testbed.invoices(world.business.id)) == invoice_count
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    assert world.testbed.notifier.sent == []
