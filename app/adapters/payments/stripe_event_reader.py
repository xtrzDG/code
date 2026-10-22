"""
What a verified Stripe event (API version 2024-06-20) tells the platform.

- checkout.session.completed (and the async_payment_* events of a session
  whose payment settles later): the first payment of a checkout, paid or
  processing, and the card it saved with the Stripe subscription and
  customer it started. A card setup pays nothing, so it brings the card
  only.
- invoice.paid / invoice.payment_failed of a later invoice: an automatic
  charge, whose parent order is in its subscription's metadata (the first
  invoice belongs to the session's event and is left to it). A charge of
  an invoice tried before (attempt_count above 1) is a retry: the dunning
  job tells the owners about it itself.
- customer.subscription.updated with a new default payment method: the
  card replaced through the billing portal.

Every other event says nothing the platform acts on.
"""

from app.adapters.payments.payment_fields import (
    read_mapping,
    read_money,
    read_reference,
)
from app.adapters.payments.stripe_cards import read_stripe_card
from app.clients.stripe.stripe_client import StripeClient
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.dto.payments import (
    PaymentMethodNotice,
    PaymentNotification,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.strings import PaymentProviderReference

CHECKOUT_COMPLETED: str = "checkout.session.completed"
CHECKOUT_ASYNC_SUCCEEDED: str = "checkout.session.async_payment_succeeded"
CHECKOUT_ASYNC_FAILED: str = "checkout.session.async_payment_failed"
INVOICE_PAID: str = "invoice.paid"
INVOICE_PAYMENT_FAILED: str = "invoice.payment_failed"
SUBSCRIPTION_UPDATED: str = "customer.subscription.updated"
FIRST_INVOICE_REASON: str = "subscription_create"
ORDER_METADATA_KEY: str = "payment_order_id"
DEFAULT_PAYMENT_METHOD_FIELD: str = "default_payment_method"
CHECKOUT_PAYMENT_STATUSES: dict[str, PaymentStatus] = {
    "paid": PaymentStatus.APPROVED,
    "unpaid": PaymentStatus.PROCESSING,
}
FIRST_ATTEMPT: int = 1


def read_stripe_event(
    event: dict[str, object], stripe_client: StripeClient
) -> VerifiedPaymentEvent:
    """
    Raises:
        ValidationFailedError: the event has no id.
        ExternalServiceError: the saved card could not be read from Stripe
            (the event is refused, so Stripe delivers it again).
    """

    event_reference: PaymentProviderReference | None = read_reference(event.get("id"))
    if event_reference is None:
        raise ValidationFailedError("Payment notification has no event id.")

    data: dict[str, object] = read_mapping(event.get("data"))
    stripe_object: dict[str, object] = read_mapping(data.get("object"))
    created: int = read_count(event.get("created"))
    match event.get("type"):
        case str(event_type) if event_type in {
            CHECKOUT_COMPLETED,
            CHECKOUT_ASYNC_SUCCEEDED,
            CHECKOUT_ASYNC_FAILED,
        }:
            return read_checkout_event(
                event_type, event_reference, stripe_object, stripe_client, created
            )
        case str(event_type) if event_type in {INVOICE_PAID, INVOICE_PAYMENT_FAILED}:
            return VerifiedPaymentEvent(
                payment=read_invoice_charge(event_type, stripe_object)
            )
        case str(event_type) if event_type == SUBSCRIPTION_UPDATED:
            return read_card_replacement(
                event_reference,
                stripe_object,
                read_mapping(data.get("previous_attributes")),
                stripe_client,
                created,
            )
        case _:
            return VerifiedPaymentEvent()


def read_checkout_event(
    event_type: str,
    event_reference: PaymentProviderReference,
    session: dict[str, object],
    stripe_client: StripeClient,
    created: int,
) -> VerifiedPaymentEvent:
    order_reference: PaymentProviderReference | None = read_reference(
        read_mapping(session.get("metadata")).get(ORDER_METADATA_KEY)
    ) or read_reference(session.get("client_reference_id"))
    if order_reference is None:
        return VerifiedPaymentEvent()

    status: PaymentStatus | None = read_checkout_status(event_type, session)
    payment: PaymentNotification | None = (
        None
        if status is None
        else PaymentNotification(
            provider=PaymentProvider.STRIPE,
            order_reference=order_reference,
            payment_reference=(
                read_reference(session.get("invoice"))
                or read_reference(session.get("id"))
            ),
            status=status,
            amount=read_money(session.get("amount_total"), session.get("currency")),
        )
    )
    if event_type != CHECKOUT_COMPLETED:
        return VerifiedPaymentEvent(payment=payment)

    schedule_reference: PaymentProviderReference | None = read_reference(
        session.get("subscription")
    )
    summary: PaymentMethodSummary | None = None
    if schedule_reference is not None:
        subscription: dict[str, object] = stripe_client.retrieve_subscription(
            str(schedule_reference)
        )
        summary = read_stripe_card(
            subscription.get(DEFAULT_PAYMENT_METHOD_FIELD), created
        )

    return VerifiedPaymentEvent(
        payment=payment,
        payment_method=PaymentMethodNotice(
            provider=PaymentProvider.STRIPE,
            order_reference=order_reference,
            event_reference=event_reference,
            summary=summary,
            schedule_reference=schedule_reference,
            customer_reference=read_reference(session.get("customer")),
        ),
    )


def read_checkout_status(
    event_type: str, session: dict[str, object]
) -> PaymentStatus | None:
    """
    The first payment's status; None when the session paid nothing (a card
    setup, or a checkout whose first charge comes at the trial's end).
    """

    if event_type == CHECKOUT_ASYNC_SUCCEEDED:
        return PaymentStatus.APPROVED

    if event_type == CHECKOUT_ASYNC_FAILED:
        return PaymentStatus.DECLINED

    raw_status: object = session.get("payment_status")
    return (
        CHECKOUT_PAYMENT_STATUSES.get(raw_status)
        if isinstance(raw_status, str)
        else None
    )


def read_invoice_charge(
    event_type: str, invoice: dict[str, object]
) -> PaymentNotification | None:
    if invoice.get("billing_reason") == FIRST_INVOICE_REASON:
        return None

    subscription_details: dict[str, object] = read_mapping(
        invoice.get("subscription_details")
    )
    parent_order_reference: PaymentProviderReference | None = read_reference(
        read_mapping(subscription_details.get("metadata")).get(ORDER_METADATA_KEY)
    )
    invoice_reference: PaymentProviderReference | None = read_reference(
        invoice.get("id")
    )
    if parent_order_reference is None or invoice_reference is None:
        return None

    is_paid: bool = event_type == INVOICE_PAID
    return PaymentNotification(
        provider=PaymentProvider.STRIPE,
        order_reference=invoice_reference,
        parent_order_reference=parent_order_reference,
        payment_reference=invoice_reference,
        status=PaymentStatus.APPROVED if is_paid else PaymentStatus.DECLINED,
        amount=read_money(
            invoice.get("amount_paid" if is_paid else "amount_due"),
            invoice.get("currency"),
        ),
        is_retry=read_count(invoice.get("attempt_count")) > FIRST_ATTEMPT,
    )


def read_card_replacement(
    event_reference: PaymentProviderReference,
    subscription: dict[str, object],
    previous_attributes: dict[str, object],
    stripe_client: StripeClient,
    created: int,
) -> VerifiedPaymentEvent:
    order_reference: PaymentProviderReference | None = read_reference(
        read_mapping(subscription.get("metadata")).get(ORDER_METADATA_KEY)
    )
    payment_method: object = subscription.get(DEFAULT_PAYMENT_METHOD_FIELD)
    if (
        order_reference is None
        or DEFAULT_PAYMENT_METHOD_FIELD not in previous_attributes
        or not isinstance(payment_method, str)
    ):
        return VerifiedPaymentEvent()

    return VerifiedPaymentEvent(
        payment_method=PaymentMethodNotice(
            provider=PaymentProvider.STRIPE,
            order_reference=order_reference,
            event_reference=event_reference,
            summary=read_stripe_card(
                stripe_client.retrieve_payment_method(payment_method), created
            ),
            schedule_reference=read_reference(subscription.get("id")),
            customer_reference=read_reference(subscription.get("customer")),
        )
    )


def read_count(raw_value: object) -> int:
    """A non-negative whole number of an event, 0 when absent or malformed."""

    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        return 0

    return max(raw_value, 0)
