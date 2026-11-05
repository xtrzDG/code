"""
When a payment provider's answer and the platform's payment order differ
in a way that moves money: the provider took money the platform has unpaid
(a lost notification), the provider failed a payment the platform has
paid, or the provider reversed a payment the platform still has paid.

What "paid here" means follows the payment the provider was asked about:
its first payment (Flitt's order, Stripe's checkout session) is paid when
the order's first payment was settled; its latest one (Stripe's latest
invoice) when the order's status is APPROVED. A newer charge of the
order's schedule than the order records differs only when the provider
took its money. Answers that are not final (created, processing) never
differ.

Which orders are asked about: checkout orders written to in the last
RECONCILIATION_WINDOW_DAYS; a Stripe order with a subscription also for
one billing interval more, since a renewal whose notification was lost
leaves its order as it was at the renewal before.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.payment_reconciliation import PaymentMismatchKind
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentStatus,
)
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_reconciliation import ProviderPaymentState

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
# Orders written to in the last week are compared: a payment whose
# notification was lost left its order as it was when the checkout opened.
RECONCILIATION_WINDOW_DAYS: int = 7
# A billing month at its longest, for the renewals of a subscription.
DAYS_PER_BILLING_MONTH: int = 31
FAILED_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.DECLINED, PaymentStatus.EXPIRED}
)


def is_reconcilable(payment_order: PaymentOrderDocument, now: Microseconds) -> bool:
    """
    A checkout order written to within its window before `now` (a card
    setup charges nothing to reconcile).
    """

    if payment_order.purpose is not PaymentOrderPurpose.CHECKOUT:
        return False

    written: int = max(int(payment_order.created_at), int(payment_order.updated_at))
    return written >= int(now) - reconciliation_window_days(payment_order) * (
        MICROSECONDS_PER_DAY
    )


def reconciliation_window_days(payment_order: PaymentOrderDocument) -> int:
    """The week, plus one billing interval for a Stripe subscription's renewals."""

    if (
        payment_order.provider is PaymentProvider.STRIPE
        and payment_order.schedule_reference is not None
    ):
        return RECONCILIATION_WINDOW_DAYS + DAYS_PER_BILLING_MONTH * int(
            payment_order.recurring_interval_months
        )

    return RECONCILIATION_WINDOW_DAYS


def find_mismatch(
    payment_order: PaymentOrderDocument, state: ProviderPaymentState
) -> PaymentMismatchKind | None:
    if not state.is_recorded_payment:
        return (
            PaymentMismatchKind.RENEWAL_PAID_AT_PROVIDER
            if state.status is PaymentStatus.APPROVED
            else None
        )

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
