"""
The payment webhooks answer at once and a worker applies what they queued
(API-03): the delivery is verified and queued without asking the provider
anything, the queued job keeps no card token in the clear, copies apply
once, and a refund or chargeback that arrives before the approval it
reverses stands (the late approval pays nothing).
"""

import json

import pytest

from app.containers.app import AppContainer
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.billing.payment_webhook.payment_notification_jobs import (
    APPLY_PAYMENT_NOTIFICATION_JOB,
    decode_payment_notification,
)
from app.use_cases.billing.payment_webhook.receive_payment_webhook_use_case import (
    ReceivePaymentWebhookUseCase,
)
from tests.billing.paid_world import checkout, payment_order
from tests.billing.queued_webhook_world import QueuedWebhookWorld

REPLAYS: int = 5


def order_of(world: QueuedWebhookWorld) -> PaymentOrderDocument:
    return payment_order(world.paid, checkout(world.paid))


def reload(
    world: QueuedWebhookWorld, order: PaymentOrderDocument
) -> PaymentOrderDocument:
    stored = world.paid.testbed.payment_order_repo.get(order.id)
    assert stored is not None
    return stored


def invoice_statuses(world: QueuedWebhookWorld) -> set[InvoiceStatus]:
    return {
        invoice.status
        for invoice in world.paid.testbed.invoices(world.paid.business.id)
    }


def test_the_webhook_queues_without_asking_the_provider_and_the_job_applies() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    parameters = world.paid.testbed.callback_parameters(
        order, "approved", payment_id=11, rectoken="card-token-secret-0001"
    )

    receipt = world.deliver(parameters)

    assert receipt.outcome is PaymentWebhookOutcome.QUEUED
    assert receipt.payment_order_id == order.id
    assert world.paid.testbed.flitt.status_queries == []
    assert invoice_statuses(world) == {InvoiceStatus.ISSUED}
    [job] = world.queue.jobs
    assert job.name == APPLY_PAYMENT_NOTIFICATION_JOB
    assert job.business_id == world.paid.business.id
    assert str(job.serial_key) == f"payment_order:{order.id}"
    assert "card-token-secret-0001" not in str(job.payload)

    assert world.run_jobs() == 1
    assert world.paid.testbed.flitt.status_queries == [str(order.id)]
    assert invoice_statuses(world) == {InvoiceStatus.PAID}
    assert reload(world, order).sealed_card_token is not None
    assert [r.outcome for r in world.documents.receipts] == [
        PaymentWebhookOutcome.APPLIED
    ]


def test_replays_apply_once_and_tell_the_owner_once() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    parameters = world.paid.testbed.callback_parameters(
        order, "declined", payment_id=12, response_description="Declined by issuer"
    )
    notices_before = len(world.paid.testbed.notifier.sent)

    queued = [world.deliver(parameters).outcome for _ in range(REPLAYS)]
    world.run_jobs()
    late = [world.deliver(parameters).outcome for _ in range(REPLAYS)]

    assert queued == [PaymentWebhookOutcome.QUEUED] * REPLAYS
    assert late == [PaymentWebhookOutcome.DUPLICATE] * REPLAYS
    assert world.queue.jobs == []
    assert reload(world, order).processed_notification_keys == ["12:declined"]
    assert invoice_statuses(world) == {InvoiceStatus.FAILED}
    assert len(world.paid.testbed.notifier.sent) == notices_before + 1


def test_replayed_approvals_pay_once_and_mail_the_invoices_once() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    parameters = world.paid.testbed.callback_parameters(
        order, "approved", payment_id=16
    )

    queued = [world.deliver(parameters).outcome for _ in range(REPLAYS)]
    world.run_jobs()
    late = [world.deliver(parameters).outcome for _ in range(REPLAYS)]

    assert queued == [PaymentWebhookOutcome.QUEUED] * REPLAYS
    assert late == [PaymentWebhookOutcome.DUPLICATE] * REPLAYS
    assert reload(world, order).processed_notification_keys == ["16:approved"]
    assert invoice_statuses(world) == {InvoiceStatus.PAID}
    # Flitt was asked once; the invoice e-mails went out once.
    assert world.paid.testbed.flitt.status_queries == [str(order.id)]
    assert [r.outcome for r in world.documents.receipts] == [
        PaymentWebhookOutcome.APPLIED
    ]


def test_an_approval_refunded_before_its_job_ran_never_pays() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    testbed = world.paid.testbed
    approved = testbed.callback_parameters(order, "approved", payment_id=17)
    world.deliver(approved)
    # Refunded at once: Flitt's record says reversed when the approval runs.
    world.deliver(testbed.callback_parameters(order, "reversed", payment_id=17))

    # The approval is not confirmed and waits; the refund overtakes it.
    assert world.run_jobs() == 1
    assert isinstance(world.failures[-1], ConflictError)
    # Its retry sees the refund: seen, nothing paid, Flitt not asked again.
    assert world.run_jobs() == 1

    stored = reload(world, order)
    assert stored.status is PaymentStatus.REVERSED
    assert stored.processed_notification_keys == ["17:reversed", "17:approved"]
    assert invoice_statuses(world) == {InvoiceStatus.ISSUED}
    assert testbed.flitt.status_queries == [str(order.id), str(order.id)]
    assert world.queue.jobs == []


def test_a_refund_before_its_approval_stands() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    testbed = world.paid.testbed
    approved = testbed.callback_parameters(order, "approved", payment_id=13)
    # Flitt's record moved on to the refund before either callback came.
    reversed_ = testbed.callback_parameters(order, "reversed", payment_id=13)

    assert world.deliver(reversed_).outcome is PaymentWebhookOutcome.QUEUED
    assert world.deliver(approved).outcome is PaymentWebhookOutcome.QUEUED
    assert world.run_jobs() == 2

    stored = reload(world, order)
    assert stored.status is PaymentStatus.REVERSED
    assert stored.processed_notification_keys == ["13:reversed", "13:approved"]
    assert invoice_statuses(world) == {InvoiceStatus.ISSUED}
    # Only the refund was read back; the late approval asked nothing.
    assert testbed.flitt.status_queries == [str(order.id)]
    # The refund was applied (no invoice paid to mail); the approval was not.
    assert [r.outcome for r in world.documents.receipts] == [
        PaymentWebhookOutcome.APPLIED
    ]
    assert world.deliver(approved).outcome is PaymentWebhookOutcome.DUPLICATE


def test_a_chargeback_after_the_payment_reverses_the_order() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    testbed = world.paid.testbed
    world.deliver(testbed.callback_parameters(order, "approved", payment_id=14))
    world.run_jobs()
    # Flitt reports a chargeback (or a refund) of the payment as reversed.
    chargeback = testbed.callback_parameters(order, "reversed", payment_id=14)

    for _ in range(REPLAYS):
        world.deliver(chargeback)
    world.run_jobs()

    stored = reload(world, order)
    assert stored.status is PaymentStatus.REVERSED
    assert stored.processed_notification_keys == ["14:approved", "14:reversed"]
    # The paid invoice stays a kept document; the platform admin settles
    # the reversal (docs/security/payments.md).
    assert invoice_statuses(world) == {InvoiceStatus.PAID}
    assert testbed.flitt.status_queries == [str(order.id), str(order.id)]


def test_a_payment_flitt_does_not_confirm_yet_is_retried_by_the_queue() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    testbed = world.paid.testbed
    parameters = testbed.callback_parameters(order, "approved", payment_id=15)
    testbed.flitt.order_states[str(order.id)] = {"order_status": "processing"}

    world.deliver(parameters)

    assert world.run_jobs() == 0
    assert isinstance(world.failures[-1], ConflictError)
    assert reload(world, order).processed_notification_keys == []
    assert invoice_statuses(world) == {InvoiceStatus.ISSUED}

    testbed.flitt.know_callback(parameters)
    assert world.run_jobs() == 1
    assert invoice_statuses(world) == {InvoiceStatus.PAID}


def test_an_unknown_order_is_refused_before_anything_is_queued() -> None:
    world = QueuedWebhookWorld()
    order = order_of(world)
    parameters = world.paid.testbed.callback_parameters(order, "approved")
    unknown = {**parameters, "order_id": str(PaymentOrderId()), "merchant_data": ""}

    with pytest.raises(NotFoundError):
        world.deliver(unknown)

    assert world.queue.jobs == []


def test_a_payload_the_platform_did_not_seal_is_refused() -> None:
    world = QueuedWebhookWorld()
    cipher = world.paid.testbed.secret_cipher

    with pytest.raises(ValidationFailedError):
        decode_payment_notification(JobPayloadJson("{}"), cipher)
    with pytest.raises(ValidationFailedError):
        decode_payment_notification(
            JobPayloadJson(
                json.dumps(
                    {"payment_order_id": str(PaymentOrderId()), "sealed_event": "x"}
                )
            ),
            cipher,
        )


def test_the_application_queues_payment_webhooks_and_its_worker_applies_them() -> None:
    container = AppContainer()

    assert isinstance(
        container.orchestrators.billing.receive_payment_webhook_use_case(),
        ReceivePaymentWebhookUseCase,
    )
    assert APPLY_PAYMENT_NOTIFICATION_JOB in container.gateways.queued_job_operators()
