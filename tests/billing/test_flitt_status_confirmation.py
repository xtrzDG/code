"""
A Flitt callback that pays or refunds takes effect only when Flitt's
status API reports the same order status and amount (API-02): a callback
signed with a leaked key, or one the order has moved past, changes nothing
and is answered 409, so Flitt sends it again.
"""

import json

import pytest

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.exceptions.application_errors import ConflictError
from tests.billing.billing_settings import sign_flitt_callback
from tests.billing.paid_world import (
    build_active_subscription,
    build_trial,
    checkout,
    payment_order,
)
from tests.billing.route_world import RouteWorld

WEBHOOK_PATH: str = "/v1/payments/flitt/webhook"


def test_an_approval_flitt_does_not_report_changes_nothing() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved", payment_id=9)
    world.testbed.flitt.order_states[str(order.id)] = {"order_status": "processing"}

    with pytest.raises(ConflictError):
        world.testbed.deliver_flitt_callback(parameters, is_known_to_flitt=False)

    assert payment_order(world, session).processed_notification_keys == []
    assert payment_order(world, session).status is not PaymentStatus.APPROVED
    assert all(
        invoice.status is InvoiceStatus.ISSUED
        for invoice in world.testbed.invoices(world.business.id)
    )
    # Flitt sends it again once its own record says approved: applied.
    receipt = world.testbed.deliver_flitt_callback(parameters)
    assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def test_an_order_flitt_does_not_know_or_another_amount_is_refused() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved")
    flitt = world.testbed.flitt

    del flitt.order_states[str(order.id)]
    with pytest.raises(ConflictError):
        world.testbed.deliver_flitt_callback(parameters, is_known_to_flitt=False)

    flitt.order_states[str(order.id)] = {
        "order_status": "approved",
        "amount": int(order.amount_minor) + 1,
        "currency": str(order.currency_code),
    }
    with pytest.raises(ConflictError):
        world.testbed.deliver_flitt_callback(parameters, is_known_to_flitt=False)

    assert payment_order(world, session).processed_notification_keys == []


def test_a_refund_is_read_back_and_a_decline_is_not() -> None:
    world, order = build_active_subscription()
    flitt = world.testbed.flitt
    queries_before = len(flitt.status_queries)
    reversed_parameters = world.testbed.callback_parameters(
        order, "reversed", payment_id=11
    )
    flitt.order_states[str(order.id)] = {"order_status": "approved"}

    with pytest.raises(ConflictError):
        world.testbed.deliver_flitt_callback(
            reversed_parameters, is_known_to_flitt=False
        )

    assert len(flitt.status_queries) == queries_before + 1
    declined = world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(order, "declined", payment_id=12)
    )
    assert declined.outcome is not PaymentWebhookOutcome.DUPLICATE
    assert len(flitt.status_queries) == queries_before + 1


def test_the_webhook_answers_409_until_flitt_confirms() -> None:
    world = RouteWorld()
    world.start_trial()
    order = world.checkout()
    parameters = world.testbed.callback_parameters(order, "approved")
    body = json.dumps(sign_flitt_callback(parameters))
    world.testbed.flitt.order_states[str(order.id)] = {"order_status": "created"}

    refused = world.client.post(
        WEBHOOK_PATH, content=body, headers={"Content-Type": "application/json"}
    )
    world.testbed.flitt.know_callback(parameters)
    applied = world.client.post(
        WEBHOOK_PATH, content=body, headers={"Content-Type": "application/json"}
    )

    assert refused.status_code == 409
    assert applied.status_code == 200
    assert applied.json()["outcome"] == "applied"
