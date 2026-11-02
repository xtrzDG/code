"""
Payment state changes as structured log lines: one logger (`app.payments`)
and a few stable event names, so a log search finds every change of one
payment order by its `payment_order_id` field. A line carries ids, the
provider, the purpose and statuses only: never card data (no masked card,
no token, no card brand), amounts or a person.
"""

import logging

from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.payment_reconciliations import PaymentMismatch
from app.schemas.domain.payments import PaymentOrderDocument
from app.utilities.observability.log_formatting import log_fields

PAYMENT_LOGGER: logging.Logger = logging.getLogger("app.payments")

# A new provider order (a checkout or a card setup) was opened.
PAYMENT_ORDER_OPENED: str = "payment_order_opened"
# A provider notification changed (or settled) a payment order.
PAYMENT_STATE_CHANGED: str = "payment_state_changed"
# The daily reconciliation found the provider disagreeing with the order.
PAYMENT_RECONCILIATION_MISMATCH: str = "payment_reconciliation_mismatch"


def log_payment_order_opened(payment_order: PaymentOrderDocument) -> None:
    PAYMENT_LOGGER.info(
        "Payment order %s opened at %s",
        payment_order.id,
        payment_order.provider.value,
        extra=log_fields(
            payment_event=PAYMENT_ORDER_OPENED,
            payment_order_id=str(payment_order.id),
            business_id=str(payment_order.business_id),
            provider=payment_order.provider.value,
            purpose=payment_order.purpose.value,
            status_after=payment_order.status.value,
        ),
    )


def log_payment_state_change(
    payment_order: PaymentOrderDocument,
    status_before: PaymentStatus,
    notified_status: PaymentStatus | None,
    outcome: PaymentWebhookOutcome,
) -> None:
    """One provider notification applied to its order (a card notice too)."""

    PAYMENT_LOGGER.info(
        "Payment order %s: %s -> %s (%s)",
        payment_order.id,
        status_before.value,
        payment_order.status.value,
        outcome.value,
        extra=log_fields(
            payment_event=PAYMENT_STATE_CHANGED,
            payment_order_id=str(payment_order.id),
            business_id=str(payment_order.business_id),
            provider=payment_order.provider.value,
            purpose=payment_order.purpose.value,
            status_before=status_before.value,
            status_after=payment_order.status.value,
            notified_status="card"
            if notified_status is None
            else notified_status.value,
            outcome=outcome.value,
            is_initial_payment_settled=int(payment_order.is_initial_payment_settled),
        ),
    )


def log_payment_mismatch(mismatch: PaymentMismatch) -> None:
    PAYMENT_LOGGER.warning(
        "Payment order %s: %s here, %s at %s (%s)",
        mismatch.payment_order_id,
        mismatch.recorded_status.value,
        mismatch.provider_status.value,
        mismatch.provider.value,
        mismatch.kind.value,
        extra=log_fields(
            payment_event=PAYMENT_RECONCILIATION_MISMATCH,
            payment_order_id=str(mismatch.payment_order_id),
            business_id=str(mismatch.business_id),
            provider=mismatch.provider.value,
            recorded_status=mismatch.recorded_status.value,
            provider_status=mismatch.provider_status.value,
            mismatch_kind=mismatch.kind.value,
        ),
    )
