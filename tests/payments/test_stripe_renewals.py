"""Stripe's automatic charges, their retries and a card replaced in its portal."""

import pytest

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentRetryOutcome,
    PaymentWebhookOutcome,
)
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.typings.billing.strings import PaymentProviderReference
from tests.billing.billing_settings import ITALY
from tests.billing.paid_world import PaidWorld, build_trial, checkout, payment_order
from tests.billing.stripe_sandbox import STRIPE_PORTAL_URL
from tests.payments.payment_world import (
    deliver_stripe,
    now_seconds,
    payment_method,
    save_card,
    stripe_invoice,
    stripe_session,
)

pytestmark = pytest.mark.usefixtures("stripe_gate_open")
MASTERCARD: dict[str, object] = {
    "id": "pm_test_0002",
    "card": {"brand": "mastercard", "last4": "4444", "exp_month": 1, "exp_year": 2031},
}


def build_stripe_subscription() -> tuple[PaidWorld, PaymentOrderDocument]:
    """An Italian business paying through Stripe, past its trial."""

    world = build_trial(ITALY)
    order = payment_order(world, checkout(world))
    deliver_stripe(
        world, "checkout.session.completed", "evt_test_0001", stripe_session(order)
    )
    world.testbed.clock.advance(days=14, hours=1)
    world.testbed.run_job(world.testbed.end_trials, "end_trials")
    assert world.testbed.subscription(world.business.id).status is (
        SubscriptionStatus.ACTIVE
    )
    return world, order


def decline_renewal(world: PaidWorld, order: PaymentOrderDocument) -> InvoiceDocument:
    world.testbed.clock.move_to(
        world.testbed.subscription(world.business.id).period_end
    )
    deliver_stripe(
        world,
        "invoice.payment_failed",
        "evt_test_0010",
        stripe_invoice(order, "in_test_0010"),
    )
    return world.testbed.invoices(world.business.id)[-1]


def run_dunning(world: PaidWorld) -> int:
    return world.testbed.run_job(
        world.testbed.payments.retry_failed_payments, "retry_failed_payments"
    )


def test_a_paid_renewal_invoices_the_next_period() -> None:
    world, order = build_stripe_subscription()
    period_end = world.testbed.subscription(world.business.id).period_end
    world.testbed.clock.move_to(period_end)
    world.testbed.clock.advance(hours=1)

    receipt = deliver_stripe(
        world, "invoice.paid", "evt_test_0002", stripe_invoice(order, "in_test_0002")
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    renewal = world.testbed.invoices(world.business.id)[-1]
    assert renewal.status is InvoiceStatus.PAID
    assert renewal.period_start == period_end
    assert renewal.provider_reference == PaymentProviderReference("in_test_0002")
    assert world.testbed.subscription(world.business.id).period_start == period_end


def test_the_first_invoice_belongs_to_the_checkout_session() -> None:
    world, order = build_stripe_subscription()
    invoices_before = len(world.testbed.invoices(world.business.id))

    receipt = deliver_stripe(
        world,
        "invoice.paid",
        "evt_test_0003",
        stripe_invoice(order, "in_test_first", billing_reason="subscription_create"),
    )

    assert receipt.outcome is PaymentWebhookOutcome.IGNORED
    assert len(world.testbed.invoices(world.business.id)) == invoices_before


def test_a_declined_renewal_starts_the_grace_and_tells_the_owner() -> None:
    world, order = build_stripe_subscription()

    failed = decline_renewal(world, order)

    assert failed.status is InvoiceStatus.FAILED
    assert failed.kind is InvoiceKind.SERVICE_PERIOD
    assert failed.provider_reference == PaymentProviderReference("in_test_0010")
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.PAST_DUE
    assert len(world.testbed.notifier.sent) == 1


def test_the_first_retry_pays_the_stripe_invoice_again() -> None:
    world, order = decline_and_wait_a_day()

    assert run_dunning(world) == 1

    assert world.testbed.stripe.paid_invoices == ["in_test_0010"]
    [retry] = world.testbed.payment_retry_repo.list_for_invoice(
        world.business.id, world.testbed.invoices(world.business.id)[-1].id
    )
    assert retry.outcome is PaymentRetryOutcome.APPROVED
    assert retry.provider is PaymentProvider.STRIPE
    assert world.testbed.stripe.idempotency_keys[-1] == f"retry:{retry.id}"
    [(_, text)] = world.testbed.notifier.sent[1:]
    assert "went through" in str(text)

    receipt = deliver_stripe(
        world,
        "invoice.paid",
        "evt_test_0011",
        stripe_invoice(order, "in_test_0010", attempt_count=2),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    retried = world.testbed.invoices(world.business.id)[-1]
    assert retried.provider_reference == PaymentProviderReference("in_test_0010")
    assert retried.status is InvoiceStatus.PAID
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.ACTIVE
    assert subscription.grace_until is None


def test_a_declined_retry_waits_for_the_next_one() -> None:
    world, order = decline_and_wait_a_day()
    world.testbed.stripe.is_card_declined = True
    invoices_before = len(world.testbed.invoices(world.business.id))

    assert run_dunning(world) == 1
    receipt = deliver_stripe(
        world,
        "invoice.payment_failed",
        "evt_test_0012",
        stripe_invoice(order, "in_test_0010", attempt_count=2),
    )

    # The invoice's decline was applied already: no second failed period.
    assert receipt.outcome is PaymentWebhookOutcome.DUPLICATE
    assert len(world.testbed.invoices(world.business.id)) == invoices_before
    [retry] = world.testbed.payment_retry_repo.list_for_invoice(
        world.business.id, world.testbed.invoices(world.business.id)[-1].id
    )
    assert retry.outcome is PaymentRetryOutcome.DECLINED
    assert str(retry.failure_reason) == "insufficient_funds"
    view = payment_method(world)
    assert view.retry is not None
    assert view.retry.last_attempt is not None
    assert int(view.retry.last_attempt) == 1
    assert view.retry.next_retry_at is not None
    assert len(world.testbed.notifier.sent) == 2
    assert run_dunning(world) == 0


def decline_and_wait_a_day() -> tuple[PaidWorld, PaymentOrderDocument]:
    world, order = build_stripe_subscription()
    decline_renewal(world, order)
    world.testbed.clock.advance(days=1, hours=1)
    return world, order


def test_the_card_is_replaced_in_the_billing_portal() -> None:
    world, order = build_stripe_subscription()

    session = save_card(world)

    assert session.provider is PaymentProvider.STRIPE
    assert str(session.url) == STRIPE_PORTAL_URL
    [portal] = world.testbed.stripe.portal_sessions
    assert portal["customer"] == "cus_test_0001"
    assert portal["flow_data[type]"] == "payment_method_update"
    assert world.testbed.stripe.checkout_sessions[1:] == []
    setup = world.testbed.payment_order_repo.get(session.payment_order_id)  # type: ignore[arg-type]
    assert setup is not None
    assert setup.purpose is PaymentOrderPurpose.CARD_SETUP

    world.testbed.stripe.payment_method = MASTERCARD
    receipt = replace_card(world, order, "evt_test_0020")

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


def test_cancelling_stops_the_stripe_subscription_and_forgets_the_card() -> None:
    world, _ = build_stripe_subscription()

    world.testbed.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=world.owner.id, business_id=world.business.id)
    )

    assert world.testbed.stripe.cancelled_subscriptions == ["sub_test_0001"]
    subscription = world.testbed.subscription(world.business.id)
    assert subscription.provider_reference is None
    assert subscription.payment_method_summary is None
    assert not payment_method(world).has_auto_debit
