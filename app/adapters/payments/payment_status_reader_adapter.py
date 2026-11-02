"""
What Flitt and Stripe say about a payment order now, for the daily
reconciliation (never for a customer's request): read-only provider calls,
no card data kept.

- Flitt: the order's status by its id (`/api/status/order_id`): the order
  is the first payment (later automatic charges are orders of their own).
- Stripe, an order with a subscription (`schedule_reference`): the
  subscription's latest invoice. The order's own invoice is compared as
  it is; a newer one the order never recorded is a renewal whose
  notification never arrived (`is_recorded_payment` False).
- Stripe, an order without one yet: its latest invoice when it names one
  (`in_...`), else the checkout session (`cs_...`).

A provider that refuses the read (Flitt's refusal, Stripe's 404 for an
object the platform got from Stripe itself) raises: the order counts as
unreadable, so revoked keys or another merchant account never pass for
"nothing to compare".
"""

from app.adapters.payments.payment_fields import read_mapping, read_reference
from app.adapters.payments.stripe_event_reader import FIRST_INVOICE_REASON, read_count
from app.clients.flitt.flitt_client import FlittClient
from app.clients.stripe.stripe_client import StripeClient
from app.contracts.platform_safety import PaymentStatusReaderAdapterContract
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.typings.billing.strings import PaymentProviderReference

STRIPE_INVOICE_PREFIX: str = "in_"
STRIPE_SESSION_PREFIX: str = "cs_"
# Stripe's invoice statuses as payment statuses ("draft" says nothing yet).
STRIPE_INVOICE_STATUSES: dict[str, PaymentStatus] = {
    "paid": PaymentStatus.APPROVED,
    "open": PaymentStatus.PROCESSING,
    "void": PaymentStatus.DECLINED,
    "uncollectible": PaymentStatus.DECLINED,
}


class PaymentStatusReaderAdapter(PaymentStatusReaderAdapterContract):
    """
    Asks the order's own provider; a provider that is not configured, an
    order with nothing to ask about yet, or an answer with nothing to
    compare (a draft, a card setup, a trial's free first invoice) says
    nothing (None).
    """

    def __init__(
        self,
        flitt_client: FlittClient | None,
        stripe_client: StripeClient | None,
    ) -> None:
        self._flitt_client: FlittClient | None = flitt_client
        self._stripe_client: StripeClient | None = stripe_client

    def read_status(
        self, payment_order: PaymentOrderDocument
    ) -> ProviderPaymentState | None:
        if payment_order.provider is PaymentProvider.FLITT:
            return self._read_flitt(payment_order)

        if self._stripe_client is None:
            return None

        if payment_order.schedule_reference is not None:
            return read_stripe_schedule(self._stripe_client, payment_order)

        return read_stripe_payment(self._stripe_client, payment_order)

    def _read_flitt(
        self, payment_order: PaymentOrderDocument
    ) -> ProviderPaymentState | None:
        if self._flitt_client is None:
            return None

        answer: dict[str, object] = self._flitt_client.read_order_status(
            str(payment_order.id)
        )
        status: PaymentStatus | None = read_known_status(answer.get("order_status"))
        if status is None:
            return None

        return ProviderPaymentState(
            reference=PaymentProviderReference(str(payment_order.id)),
            status=status,
            is_first_payment=True,
        )


def read_stripe_payment(
    stripe_client: StripeClient, payment_order: PaymentOrderDocument
) -> ProviderPaymentState | None:
    """The invoice or checkout session the order records."""

    reference: PaymentProviderReference | None = payment_order.last_payment_reference
    if reference is None:
        return None

    if str(reference).startswith(STRIPE_INVOICE_PREFIX):
        invoice = stripe_client.retrieve_invoice(str(reference))
        status = STRIPE_INVOICE_STATUSES.get(str(invoice.get("status")))
        is_first_payment = False
    elif str(reference).startswith(STRIPE_SESSION_PREFIX):
        session = stripe_client.retrieve_checkout_session(str(reference))
        status = read_session_status(session)
        is_first_payment = True
    else:
        return None

    if status is None:
        return None

    return ProviderPaymentState(
        reference=reference, status=status, is_first_payment=is_first_payment
    )


def read_stripe_schedule(
    stripe_client: StripeClient, payment_order: PaymentOrderDocument
) -> ProviderPaymentState | None:
    """The latest invoice of the order's subscription, recorded or not."""

    subscription: dict[str, object] = (
        stripe_client.retrieve_subscription_latest_invoice(
            str(payment_order.schedule_reference)
        )
    )
    invoice: dict[str, object] = read_mapping(subscription.get("latest_invoice"))
    reference: PaymentProviderReference | None = read_reference(invoice.get("id"))
    status: PaymentStatus | None = STRIPE_INVOICE_STATUSES.get(
        str(invoice.get("status"))
    )
    if reference is None or status is None:
        return None

    is_recorded: bool = reference == payment_order.last_payment_reference
    if not is_recorded and not is_unrecorded_charge(invoice):
        return None

    return ProviderPaymentState(
        reference=reference,
        status=status,
        is_first_payment=False,
        is_recorded_payment=is_recorded,
    )


def is_unrecorded_charge(invoice: dict[str, object]) -> bool:
    """
    A newer invoice that charged money: not the subscription's first one
    (the checkout's own notification carries it; with a trial it is free).
    """

    return (
        invoice.get("billing_reason") != FIRST_INVOICE_REASON
        and read_count(invoice.get("amount_paid")) > 0
    )


def read_known_status(raw_status: object) -> PaymentStatus | None:
    """A Flitt `order_status` the platform knows, else None."""

    try:
        return PaymentStatus(str(raw_status).strip().lower())
    except ValueError:
        return None


def read_session_status(session: dict[str, object]) -> PaymentStatus | None:
    """
    A checkout session's first payment: paid (APPROVED), expired unpaid
    (EXPIRED), open (PROCESSING); a session that pays nothing now (a card
    setup, a trial) has no payment to compare (None).
    """

    payment_status: object = session.get("payment_status")
    if payment_status == "paid":
        return PaymentStatus.APPROVED

    if payment_status != "unpaid":
        return None

    if session.get("status") == "expired":
        return PaymentStatus.EXPIRED

    return PaymentStatus.PROCESSING if read_reference(session.get("id")) else None
