"""A retry of a declined automatic charge settles the invoice it retried."""

from typed_time_provider import Microseconds

from app.contracts.payment_methods import PaymentRetryRepoContract
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentNotification
from app.schemas.typings.billing.prefixed_id import PaymentRetryId
from app.use_cases.shared.billing_records import (
    OPEN_INVOICE_STATUSES,
    list_subscription_invoices,
)
from app.use_cases.shared.invoice_payments import record_invoice_payment
from app.utilities.billing.payment_retry_identity import parse_payment_retry_id


def find_retried_invoice(
    retry_repo: PaymentRetryRepoContract,
    invoice_repo: InvoiceRepoContract,
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
    notification: PaymentNotification,
) -> InvoiceDocument | None:
    """
    The unpaid invoice a retry charged for: named by the retry (a charge
    sent under the retry's id) or carrying the provider's charge (Stripe
    pays its own invoice again). None for any other charge.
    """

    if not notification.is_retry:
        return None

    retry_id: PaymentRetryId | None = parse_payment_retry_id(
        notification.order_reference
    )
    if retry_id is not None:
        attempt: PaymentRetryAttemptDocument | None = retry_repo.get(
            payment_order.business_id, retry_id
        )
        return (
            None
            if attempt is None
            else invoice_repo.get(payment_order.business_id, attempt.invoice_id)
        )

    return next(
        (
            invoice
            for invoice in list_subscription_invoices(invoice_repo, subscription)
            if notification.payment_reference is not None
            and invoice.provider_reference == notification.payment_reference
        ),
        None,
    )


def settle_retried_invoice(
    invoice_repo: InvoiceRepoContract,
    invoice: InvoiceDocument,
    notification: PaymentNotification,
    now: Microseconds,
) -> InvoiceDocument:
    """The retried invoice is PAID with the retry's charge (its receipt)."""

    if invoice.status not in OPEN_INVOICE_STATUSES:
        return invoice

    record_invoice_payment(invoice, InvoiceStatus.PAID, notification.card, now)
    if notification.payment_reference is not None:
        invoice.provider_reference = notification.payment_reference

    invoice.updated_at = now
    invoice_repo.save(invoice)
    return invoice
