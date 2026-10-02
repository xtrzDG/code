"""Flitt payment notifications: authenticity, matching orders and idempotency."""

import json
from urllib.parse import urlencode

import pytest

from app.schemas.constants.billing import InvoiceStatus, SubscriptionStatus
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from tests.billing.billing_settings import sign_flitt_callback
from tests.billing.paid_world import build_trial, checkout, pay, payment_order


def test_approved_payment_during_the_trial_pays_ahead_and_keeps_the_trial() -> None:
    world = build_trial()
    session = checkout(world)

    pay(world, session, payment_id=555)

    subscription = world.testbed.subscription(world.business.id)
    assert subscription.status is SubscriptionStatus.TRIALING
    assert str(subscription.provider_reference) == str(session.payment_order_id)
    invoices = world.testbed.invoices(world.business.id)
    assert all(invoice.status is InvoiceStatus.PAID for invoice in invoices)
    assert {str(invoice.provider_reference) for invoice in invoices} == {"555"}
    assert payment_order(world, session).status is PaymentStatus.APPROVED
    assert world.testbed.notifier.sent == []


def test_repeated_notifications_change_nothing() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved", payment_id=7)
    first = world.testbed.deliver_flitt_callback(parameters)
    invoices_after_first = world.testbed.invoices(world.business.id)

    second = world.testbed.deliver_flitt_callback(parameters)

    assert first.outcome is PaymentWebhookOutcome.APPLIED
    assert second.outcome is PaymentWebhookOutcome.DUPLICATE
    assert second.payment_order_id == order.id
    assert world.testbed.invoices(world.business.id) == invoices_after_first
    assert payment_order(world, session).processed_notification_keys == ["7:approved"]


def test_forged_or_unsigned_notifications_are_refused() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved")
    signed = sign_flitt_callback(parameters)

    for forged in (
        parameters,
        {**signed, "signature": "0" * 40},
        {**signed, "amount": 1},
        {**signed, "order_status": "declined"},
    ):
        with pytest.raises(AccessDeniedError):
            world.testbed.deliver_flitt_callback(forged, is_signed=False)

    assert all(
        invoice.status is InvoiceStatus.ISSUED
        for invoice in world.testbed.invoices(world.business.id)
    )
    assert payment_order(world, session).processed_notification_keys == []


def test_notifications_for_unknown_orders_are_not_found() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    stranger = order.model_copy(update={"id": PaymentOrderId()})

    with pytest.raises(NotFoundError):
        world.testbed.deliver_flitt_callback(
            {
                **world.testbed.callback_parameters(stranger, "approved"),
                "merchant_data": "not-ours",
            }
        )


def test_approved_amount_must_match_the_order() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    with pytest.raises(ValidationFailedError):
        world.testbed.deliver_flitt_callback(
            world.testbed.callback_parameters(order, "approved", amount=51700)
        )

    with pytest.raises(ValidationFailedError):
        world.testbed.deliver_flitt_callback(
            {
                **world.testbed.callback_parameters(order, "approved"),
                "currency": "EUR",
            }
        )

    assert payment_order(world, session).processed_notification_keys == []


def test_form_encoded_notifications_are_accepted() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved"),
        content_type="application/x-www-form-urlencoded",
        encoder=lambda parameters: urlencode(
            {key: str(value) for key, value in parameters.items()}
        ),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def test_other_statuses_are_recorded_only() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    processing = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "processing")
    )
    expired = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "expired")
    )

    assert processing.outcome is PaymentWebhookOutcome.IGNORED
    assert expired.outcome is PaymentWebhookOutcome.IGNORED
    assert payment_order(world, session).status is PaymentStatus.EXPIRED
    assert all(
        invoice.status is InvoiceStatus.ISSUED
        for invoice in world.testbed.invoices(world.business.id)
    )
    assert world.testbed.notifier.sent == []


def test_reversal_is_recorded_for_the_admin() -> None:
    world = build_trial()
    session = checkout(world)
    pay(world, session)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "reversed", payment_id=1)
    )
    late_processing = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "processing", payment_id=9)
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED
    assert late_processing.outcome is PaymentWebhookOutcome.IGNORED
    assert payment_order(world, session).status is PaymentStatus.REVERSED


def test_webhook_body_round_trips_as_json_text() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "approved"),
        encoder=lambda parameters: json.dumps({"response": parameters}),
    )

    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def test_a_second_payment_for_paid_bills_keeps_them_paid() -> None:
    world = build_trial()
    first = checkout(world)
    second = checkout(world)
    pay(world, first, payment_id=1)

    receipt = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            payment_order(world, second), "approved", payment_id=2
        )
    )

    invoices = world.testbed.invoices(world.business.id)
    assert {str(invoice.provider_reference) for invoice in invoices} == {"1"}
    assert str(world.testbed.subscription(world.business.id).provider_reference) == (
        str(second.payment_order_id)
    )
    # Only one schedule keeps running, and the money paid twice is refunded.
    assert world.testbed.flitt.stopped_orders == [str(first.payment_order_id)]
    assert receipt.outcome is PaymentWebhookOutcome.REFUND_DUE
    assert payment_order(world, second).is_refund_due
    assert not payment_order(world, first).is_refund_due


def test_payment_for_a_missing_subscription_is_not_found() -> None:
    world = build_trial()
    session = checkout(world)
    orphan = payment_order(world, session).model_copy(
        update={"id": PaymentOrderId(), "subscription_id": SubscriptionId()}
    )
    world.testbed.payment_order_repo.save(orphan)

    with pytest.raises(NotFoundError):
        world.testbed.deliver_flitt_callback(
            world.testbed.callback_parameters(orphan, "approved")
        )
