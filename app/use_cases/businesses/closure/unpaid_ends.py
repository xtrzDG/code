"""When a business's service stopped being paid for (automatic offboarding)."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.use_cases.shared.billing_records import find_covering_paid_invoice


def unpaid_end(
    subscription: SubscriptionDocument | None,
    invoices: list[InvoiceDocument],
    now: Microseconds,
) -> Microseconds | None:
    """
    The moment the subscription ended without payment, if it has: a missed
    payment whose grace ran out (PAST_DUE, at `grace_until`), or a cancelled
    subscription past the last period paid for. None while the service is
    paid for (a trial, an active or paused subscription, grace still
    running), and for a business that never paid (INCOMPLETE, or no
    subscription: it may still be setting up).
    """

    if subscription is None:
        return None

    if subscription.status is SubscriptionStatus.PAST_DUE:
        grace_until: Microseconds | None = subscription.grace_until
        return grace_until if grace_until is not None and now >= grace_until else None

    if subscription.status is not SubscriptionStatus.CANCELLED:
        return None

    if find_covering_paid_invoice(invoices, now) is not None:
        return None

    paid_until: int = max(
        [int(subscription.period_end)]
        + [
            int(invoice.period_end)
            for invoice in invoices
            if invoice.kind is InvoiceKind.SERVICE_PERIOD
            and invoice.status is InvoiceStatus.PAID
        ]
    )
    return Microseconds(paid_until) if now >= paid_until else None
