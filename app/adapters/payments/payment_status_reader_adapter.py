"""
What Flitt and Stripe say about a payment order now, for the daily
reconciliation (never for a customer's request): read-only provider calls,
no card data kept.

- Flitt: the order's status by its id (`/api/status/order_id`): the order
  is the first payment (later automatic charges are orders of their own).
- Stripe: the latest invoice when the order names one (`in_...`), else the
  checkout session (`cs_...`): paid, open, void or expired.
"""

from app.adapters.payments.payment_fields import read_reference
from app.clients.flitt.flitt_client import FlittClient
from app.clients.stripe.stripe_client import StripeClient, StripeNotFoundError
from app.contracts.platform_safety import PaymentStatusReaderAdapterContract
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_reconciliation import ProviderPaymentState
from app.schemas.exceptions.payment_errors import PaymentProviderRefusedError
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
    Asks the order's own provider; a provider that is not configured, or
    that does not know the order (Flitt's refusal, Stripe's 404), has
    nothing to say (None).
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

        return self._read_stripe(payment_order)

    def _read_flitt(
        self, payment_order: PaymentOrderDocument
    ) -> ProviderPaymentState | None:
        if self._flitt_client is None:
            return None

        try:
            answer: dict[str, object] = self._flitt_client.read_order_status(
                str(payment_order.id)
            )
        except PaymentProviderRefusedError:
            return None

        status: PaymentStatus | None = read_known_status(answer.get("order_status"))
        if status is None:
            return None

        return ProviderPaymentState(
            reference=PaymentProviderReference(str(payment_order.id)),
            status=status,
            is_first_payment=True,
        )

    def _read_stripe(
        self, payment_order: PaymentOrderDocument
    ) -> ProviderPaymentState | None:
        reference: PaymentProviderReference | None = (
            payment_order.last_payment_reference
        )
        if self._stripe_client is None or reference is None:
            return None

        try:
            if str(reference).startswith(STRIPE_INVOICE_PREFIX):
                invoice = self._stripe_client.retrieve_invoice(str(reference))
                status = STRIPE_INVOICE_STATUSES.get(str(invoice.get("status")))
                is_first_payment = False
            elif str(reference).startswith(STRIPE_SESSION_PREFIX):
                session = self._stripe_client.retrieve_checkout_session(
                    str(reference)
                )
                status = read_session_status(session)
                is_first_payment = True
            else:
                return None
        except StripeNotFoundError:
            return None

        if status is None:
            return None

        return ProviderPaymentState(
            reference=reference,
            status=status,
            is_first_payment=is_first_payment,
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
