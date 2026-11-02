"""
Copies of one payment notification that arrive together (two API
instances, a provider retrying while the first copy is still applied):
the order's notification lock makes them apply once (API-03).
"""

import threading
from concurrent.futures import ThreadPoolExecutor

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.payments import PaymentWebhookReceipt
from tests.billing.paid_world import build_trial, checkout, payment_order

COPIES: int = 5


def test_concurrent_copies_of_one_notification_apply_once() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved", payment_id=7)
    # Reading the payment back takes a while: without the lock every copy
    # would pass the duplicate check before the first one stored its key.
    world.testbed.flitt.status_delay_seconds = 0.2
    start = threading.Barrier(COPIES)

    def deliver(copy: int) -> PaymentWebhookReceipt:
        del copy
        start.wait()
        return world.testbed.deliver_flitt_callback(parameters)

    with ThreadPoolExecutor(max_workers=COPIES) as pool:
        receipts = list(pool.map(deliver, range(COPIES)))

    outcomes = sorted(receipt.outcome.value for receipt in receipts)
    assert outcomes == sorted(
        [PaymentWebhookOutcome.APPLIED.value]
        + [PaymentWebhookOutcome.DUPLICATE.value] * (COPIES - 1)
    )
    assert payment_order(world, session).processed_notification_keys == ["7:approved"]
    # Only the copy that applied asked Flitt; the duplicates stopped before.
    assert world.testbed.flitt.status_queries == [str(order.id)]
    invoices = world.testbed.invoices(world.business.id)
    assert all(invoice.status is InvoiceStatus.PAID for invoice in invoices)


def test_sequential_replays_apply_once_and_ask_the_provider_once() -> None:
    world = build_trial()
    session = checkout(world)
    order = payment_order(world, session)
    parameters = world.testbed.callback_parameters(order, "approved", payment_id=8)

    receipts = [world.testbed.deliver_flitt_callback(parameters) for _ in range(5)]

    assert [receipt.outcome for receipt in receipts] == [
        PaymentWebhookOutcome.APPLIED,
        *[PaymentWebhookOutcome.DUPLICATE] * 4,
    ]
    assert world.testbed.flitt.status_queries == [str(order.id)]
