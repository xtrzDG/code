"""
When a payment provider's answer and the platform's payment order differ
in a way that moves money: the provider took money the platform has unpaid
(a lost notification), the provider failed a payment the platform has
paid, or the provider reversed a payment the platform still has paid.

What "paid here" means follows the payment the provider was asked about:
its first payment (Flitt's order, Stripe's checkout session) is paid when
the order's first payment was settled; its latest one (Stripe's latest
invoice) when the order's status is APPROVED. Answers that are not final
(created, processing) never differ.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import PaymentOrderPurpose, PaymentStatus
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_reconciliation import ProviderPaymentState

FAILED_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.DECLINED, PaymentStatus.EXPIRED}
)


def is_reconcilable(payment_order: PaymentOrderDocument, since: Microseconds) -> bool:
    """
    A checkout order written to since `since` (a card setup charges
    nothing to reconcile).
    """

    if payment_order.purpose is not PaymentOrderPurpose.CHECKOUT:
        return False

    return max(int(payment_order.created_at), int(payment_order.updated_at)) >= int(
        since
    )


def find_mismatch(
    payment_order: PaymentOrderDocument, state: ProviderPaymentState
) -> PaymentMismatchKind | None:
    recorded_reversed: bool = payment_order.status is PaymentStatus.REVERSED
    recorded_paid: bool = not recorded_reversed and (
        payment_order.is_initial_payment_settled
        if state.is_first_payment
        else payment_order.status is PaymentStatus.APPROVED
    )
    if state.status is PaymentStatus.APPROVED and not (
        recorded_paid or recorded_reversed
    ):
        return PaymentMismatchKind.PAID_AT_PROVIDER

    if state.status in FAILED_STATUSES and recorded_paid:
        return PaymentMismatchKind.FAILED_AT_PROVIDER

    if state.status is PaymentStatus.REVERSED and not recorded_reversed:
        return PaymentMismatchKind.REVERSED_AT_PROVIDER

    return None
