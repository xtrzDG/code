"""Businesses that pay through Flitt or Stripe, and their providers' notices."""

from typing import Any

from app.schemas.constants.payments import PaymentProvider, PaymentWebhookOutcome
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_methods import (
    CardSetupSessionView,
    PaymentMethodQuery,
    PaymentMethodView,
    StartCardSetupCommand,
    StartCardSetupRequest,
)
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookSignature,
)
from tests.billing.paid_world import PaidWorld, checkout, payment_order
from tests.billing.stripe_sandbox import sign_stripe_event, stripe_event

MICROSECONDS_PER_SECOND: int = 1_000_000
CARD_TOKEN: str = "rectoken-test-0000"
CARD_FIELDS: dict[str, object] = {
    "masked_card": "444455XXXXXX1111",
    "card_type": "VISA",
    "rectoken": CARD_TOKEN,
    "rectoken_lifetime": "01.09.2029 00:00:00",
}


def flitt_pay_with_card(
    world: PaidWorld, payment_id: int = 1, **extra: Any
) -> PaymentOrderDocument:
    """The owner checks out and pays; Flitt saves the card (its token)."""

    order = payment_order(world, checkout(world))
    world.testbed.deliver_flitt_callback(
        card_callback(world, order, "approved", payment_id, **extra)
    )
    return reload(world, order)


def card_callback(
    world: PaidWorld,
    order: PaymentOrderDocument,
    status: str,
    payment_id: int,
    amount: int | None = None,
    **fields: object,
) -> dict[str, object]:
    """A Flitt callback of the order that carries the saved card's fields."""

    return {
        **world.testbed.callback_parameters(
            order, status, payment_id=payment_id, amount=amount
        ),
        **CARD_FIELDS,
        **fields,
    }


def reload(world: PaidWorld, order: PaymentOrderDocument) -> PaymentOrderDocument:
    stored = world.testbed.payment_order_repo.get(order.id)
    assert stored is not None
    return stored


def now_seconds(world: PaidWorld) -> int:
    return int(world.testbed.clock.now()) // MICROSECONDS_PER_SECOND


def deliver_stripe(
    world: PaidWorld,
    event_type: str,
    event_id: str,
    stripe_object: dict[str, object],
    previous: dict[str, object] | None = None,
    signed_at: int | None = None,
    created: int | None = None,
) -> PaymentWebhookReceipt:
    payload: str = stripe_event(
        event_type, event_id, stripe_object, created or now_seconds(world), previous
    )
    signature: str = sign_stripe_event(payload, signed_at or now_seconds(world))
    return world.testbed.process_webhook.run(
        PaymentWebhookDelivery(
            body=PaymentWebhookBody(payload),
            provider=PaymentProvider.STRIPE,
            signature=PaymentWebhookSignature(signature),
        )
    )


def stripe_session(
    order: PaymentOrderDocument,
    payment_status: str = "paid",
    subscription_id: str = "sub_test_0001",
) -> dict[str, object]:
    return {
        "id": "cs_test_0000",
        "client_reference_id": str(order.id),
        "metadata": {"payment_order_id": str(order.id)},
        "subscription": subscription_id,
        "customer": "cus_test_0001",
        "invoice": "in_test_first",
        "amount_total": int(order.amount_minor),
        "currency": str(order.currency_code).lower(),
        "payment_status": payment_status,
    }


def stripe_invoice(
    order: PaymentOrderDocument,
    invoice_id: str,
    attempt_count: int = 1,
    billing_reason: str = "subscription_cycle",
) -> dict[str, object]:
    return {
        "id": invoice_id,
        "billing_reason": billing_reason,
        "subscription": "sub_test_0001",
        "subscription_details": {"metadata": {"payment_order_id": str(order.id)}},
        "amount_paid": int(order.recurring_amount_minor),
        "amount_due": int(order.recurring_amount_minor),
        "currency": str(order.currency_code).lower(),
        "attempt_count": attempt_count,
    }


def payment_method(world: PaidWorld) -> PaymentMethodView:
    return world.testbed.payments.get_payment_method.run(
        PaymentMethodQuery(user_id=world.owner.id, business_id=world.business.id)
    )


def save_card(world: PaidWorld) -> CardSetupSessionView:
    return world.testbed.payments.start_card_setup.run(
        StartCardSetupCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            request=StartCardSetupRequest(),
        )
    )


def setup_order(world: PaidWorld) -> PaymentOrderDocument:
    """The owner saves a card: the card setup order it opened."""

    session = save_card(world)
    assert session.payment_order_id is not None
    order = world.testbed.payment_order_repo.get(session.payment_order_id)
    assert order is not None
    return order


def confirm_card(
    world: PaidWorld, order: PaymentOrderDocument, payment_id: int = 7, **extra: object
) -> PaymentWebhookOutcome:
    """Flitt verified the card of a card setup (nothing charged) and saved it."""

    return world.testbed.deliver_flitt_callback(
        card_callback(world, order, "approved", payment_id, amount=0, **extra)
    ).outcome
