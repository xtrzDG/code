"""
A retry the provider approved (or is still processing) settles its invoice
by notice: no further retry charges the card meanwhile, and a charge that
finds its invoice already paid is owed back.
"""

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.payments import PaymentRetryOutcome, PaymentWebhookOutcome
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.utilities.billing.payment_retry_identity import derive_payment_retry_id
from tests.billing.paid_world import PaidWorld
from tests.payments.payment_world import reload
from tests.payments.test_dunning_retries import (
    DAY_HOURS,
    build_declined_charge,
    retries,
    run_dunning,
)


def deliver_retry(
    world: PaidWorld,
    order: PaymentOrderDocument,
    retry: PaymentRetryAttemptDocument,
    status: str,
    payment_id: int,
) -> PaymentWebhookOutcome:
    return world.testbed.deliver_flitt_callback(
        {
            **world.testbed.callback_parameters(
                order,
                status,
                payment_id=payment_id,
                amount=int(order.recurring_amount_minor),
            ),
            "order_id": str(retry.id),
        }
    ).outcome


def stored_invoice(world: PaidWorld, invoice: InvoiceDocument) -> InvoiceDocument:
    [stored] = [
        candidate
        for candidate in world.testbed.invoices(world.business.id)
        if candidate.id == invoice.id
    ]
    return stored


def test_no_retry_charges_the_card_while_an_approved_one_awaits_its_notice() -> None:
    world, _, invoice = build_declined_charge()
    world.testbed.clock.advance(hours=DAY_HOURS)
    assert run_dunning(world) == 1
    world.testbed.clock.advance(hours=2 * DAY_HOURS)

    assert run_dunning(world) == 0

    assert len(world.testbed.flitt.recurring_orders) == 1
    assert [
        (int(retry.attempt), retry.outcome) for retry in retries(world, invoice)
    ] == [(1, PaymentRetryOutcome.APPROVED)]


def test_a_processing_retry_holds_the_next_until_its_decline_arrives() -> None:
    world, order, invoice = build_declined_charge()
    world.testbed.flitt.recurring_status = "processing"
    world.testbed.clock.advance(hours=DAY_HOURS)
    run_dunning(world)
    world.testbed.clock.advance(hours=2 * DAY_HOURS)
    assert run_dunning(world) == 0
    [first] = retries(world, invoice)
    assert first.outcome is PaymentRetryOutcome.PROCESSING

    assert deliver_retry(world, order, first, "declined", 71) is (
        PaymentWebhookOutcome.IGNORED
    )

    assert retries(world, invoice)[0].outcome is PaymentRetryOutcome.DECLINED
    world.testbed.flitt.recurring_status = "declined"
    assert run_dunning(world) == 1
    assert len(world.testbed.flitt.recurring_orders) == 2


def test_the_notice_of_an_approved_retry_records_it_and_pays_the_invoice() -> None:
    world, order, invoice = build_declined_charge()
    world.testbed.flitt.recurring_status = "processing"
    world.testbed.clock.advance(hours=DAY_HOURS)
    run_dunning(world)
    [first] = retries(world, invoice)

    assert deliver_retry(world, order, first, "approved", 72) is (
        PaymentWebhookOutcome.APPLIED
    )

    assert retries(world, invoice)[0].outcome is PaymentRetryOutcome.APPROVED
    assert stored_invoice(world, invoice).status is InvoiceStatus.PAID


def test_a_second_approved_retry_of_a_paid_invoice_is_owed_back() -> None:
    world, order, invoice = build_declined_charge()
    world.testbed.clock.advance(hours=DAY_HOURS)
    run_dunning(world)
    [first] = retries(world, invoice)
    # A second charge of the same invoice (sent before this release, or by
    # a provider that retried on its own) whose notice comes last.
    second = first.model_copy(
        update={
            "id": derive_payment_retry_id(invoice.id, PaymentRetryAttempt(2)),
            "attempt": PaymentRetryAttempt(2),
        }
    )
    assert world.testbed.payment_retry_repo.claim(second)

    paid = deliver_retry(world, order, first, "approved", 73)
    owed = deliver_retry(world, order, second, "approved", 74)

    assert (paid, owed) == (
        PaymentWebhookOutcome.APPLIED,
        PaymentWebhookOutcome.REFUND_DUE,
    )
    assert reload(world, order).is_refund_due
    assert stored_invoice(world, invoice).status is InvoiceStatus.PAID
