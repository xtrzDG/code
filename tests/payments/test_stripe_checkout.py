"""Owners in the EU, the US and Israel pay through Stripe Checkout."""

import pytest

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentStatus,
    PaymentWebhookOutcome,
)
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentWebhookDelivery
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.billing.strings import (
    PaymentProviderReference,
    PaymentWebhookBody,
    PaymentWebhookSignature,
)
from tests.billing.billing_settings import (
    CABINET_ORIGIN,
    ISRAEL,
    ITALY,
    USA,
    CountryPreset,
)
from tests.billing.paid_world import PaidWorld, build_trial, checkout, payment_order
from tests.billing.stripe_sandbox import STRIPE_CHECKOUT_URL, stripe_event
from tests.payments.payment_world import (
    deliver_stripe,
    now_seconds,
    reload,
    stripe_session,
)

pytestmark = pytest.mark.usefixtures("stripe_gate_open")
MICROSECONDS_PER_SECOND: int = 1_000_000


def stripe_checkout(world: PaidWorld) -> PaymentOrderDocument:
    session = checkout(world, return_url=f"{CABINET_ORIGIN}/b/billing")
    assert str(session.checkout_url) == STRIPE_CHECKOUT_URL
    return payment_order(world, session)


def complete(world: PaidWorld, order: PaymentOrderDocument) -> PaymentWebhookOutcome:
    return deliver_stripe(
        world, "checkout.session.completed", "evt_test_0001", stripe_session(order)
    ).outcome


@pytest.mark.parametrize("country", [ITALY, USA, ISRAEL])
def test_the_checkout_is_a_stripe_subscription_session(country: CountryPreset) -> None:
    world = build_trial(country)
    order = stripe_checkout(world)

    assert order.provider is PaymentProvider.STRIPE
    assert order.purpose is PaymentOrderPurpose.CHECKOUT
    [form] = world.testbed.stripe.checkout_sessions
    assert form["mode"] == "subscription"
    assert form["client_reference_id"] == str(order.id)
    assert form["metadata[payment_order_id]"] == str(order.id)
    assert form["subscription_data[metadata][payment_order_id]"] == str(order.id)
    assert form["success_url"] == f"{CABINET_ORIGIN}/b/billing"
    assert form["line_items[0][price_data][recurring][interval]"] == "month"
    assert form["line_items[0][price_data][unit_amount]"] == str(
        int(order.recurring_amount_minor)
    )
    assert form["line_items[0][price_data][currency]"] == (
        str(order.currency_code).lower()
    )
    assert form["line_items[1][price_data][unit_amount]"] == str(
        int(order.amount_minor)
    )
    assert "line_items[1][price_data][recurring][interval]" not in form
    assert world.testbed.stripe.idempotency_keys == [f"checkout:{order.id}"]


def test_the_automatic_charges_start_when_the_paid_period_ends() -> None:
    world = build_trial(ITALY)
    stripe_checkout(world)
    paid_until = max(
        int(invoice.period_end)
        for invoice in world.testbed.invoices(world.business.id)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
    )
    form = world.testbed.stripe.checkout_sessions[-1]

    assert int(form["subscription_data[trial_end]"]) == (
        paid_until // MICROSECONDS_PER_SECOND
    )
    assert "subscription_data[billing_cycle_anchor]" not in form
    assert form["locale"] == "it"


def test_a_paid_session_pays_the_bills_and_saves_the_card() -> None:
    world = build_trial(ITALY)
    order = stripe_checkout(world)

    assert complete(world, order) is PaymentWebhookOutcome.APPLIED

    stored = reload(world, order)
    assert stored.status is PaymentStatus.APPROVED
    assert stored.schedule_reference == PaymentProviderReference("sub_test_0001")
    assert stored.customer_reference == PaymentProviderReference("cus_test_0001")
    assert stored.sealed_card_token is None
    assert all(
        invoice.status is InvoiceStatus.PAID
        for invoice in world.testbed.invoices(world.business.id)
    )
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert subscription.payment_provider is PaymentProvider.STRIPE
    assert subscription.provider_reference == PaymentProviderReference("sub_test_0001")
    summary = subscription.payment_method_summary
    assert summary is not None
    assert summary.provider is PaymentProvider.STRIPE
    assert (str(summary.brand), str(summary.last_digits)) == ("VISA", "4242")
    assert (int(summary.expiry_month or 0), int(summary.expiry_year or 0)) == (9, 2030)


def test_the_same_event_is_applied_once() -> None:
    world = build_trial(ITALY)
    order = stripe_checkout(world)
    complete(world, order)

    assert complete(world, order) is PaymentWebhookOutcome.DUPLICATE


def test_a_session_still_settling_waits_for_its_async_result() -> None:
    world = build_trial(ITALY)
    order = stripe_checkout(world)

    deliver_stripe(
        world,
        "checkout.session.completed",
        "evt_test_0002",
        stripe_session(order, payment_status="unpaid"),
    )
    assert reload(world, order).status is PaymentStatus.PROCESSING
    assert all(
        invoice.status is not InvoiceStatus.PAID
        for invoice in world.testbed.invoices(world.business.id)
    )

    receipt = deliver_stripe(
        world,
        "checkout.session.async_payment_succeeded",
        "evt_test_0003",
        stripe_session(order),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    assert reload(world, order).status is PaymentStatus.APPROVED


def test_a_failed_async_payment_fails_the_bills() -> None:
    world = build_trial(ITALY)
    order = stripe_checkout(world)

    deliver_stripe(
        world,
        "checkout.session.async_payment_failed",
        "evt_test_0004",
        stripe_session(order, payment_status="unpaid"),
    )

    assert reload(world, order).status is PaymentStatus.DECLINED
    assert {
        invoice.status for invoice in world.testbed.invoices(world.business.id)
    } == {InvoiceStatus.FAILED}


def test_an_unsigned_stale_or_forged_event_is_refused() -> None:
    world = build_trial(ITALY)
    order = stripe_checkout(world)

    with pytest.raises(AccessDeniedError):
        deliver_stripe(
            world,
            "checkout.session.completed",
            "evt_test_0005",
            stripe_session(order),
            signed_at=now_seconds(world) - 301,
        )

    with pytest.raises(AccessDeniedError):
        world.testbed.process_webhook.run(unsigned_delivery(world, order))

    with pytest.raises(AccessDeniedError):
        world.testbed.process_webhook.run(
            unsigned_delivery(world, order, "t=1,v1=0000")
        )

    assert reload(world, order).status is not PaymentStatus.APPROVED


def unsigned_delivery(
    world: PaidWorld, order: PaymentOrderDocument, signature: str | None = None
) -> PaymentWebhookDelivery:
    return PaymentWebhookDelivery(
        body=PaymentWebhookBody(
            stripe_event(
                "checkout.session.completed",
                "evt_test_0006",
                stripe_session(order),
                now_seconds(world),
            )
        ),
        provider=PaymentProvider.STRIPE,
        signature=None if signature is None else PaymentWebhookSignature(signature),
    )


def test_events_the_platform_does_not_use_are_ignored() -> None:
    world = build_trial(ITALY)
    order = stripe_checkout(world)

    receipt = deliver_stripe(
        world, "customer.created", "evt_test_0007", {"id": "cus_test_0001"}
    )

    assert receipt.outcome is PaymentWebhookOutcome.IGNORED
    assert reload(world, order).status is not PaymentStatus.APPROVED
