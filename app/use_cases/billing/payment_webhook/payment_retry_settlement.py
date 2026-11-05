"""A retry of a declined automatic charge settles the invoice it retried."""

from typed_time_provider import Microseconds

from app.contracts.payment_methods import PaymentRetryRepoContract
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.payments import PaymentRetryOutcome, PaymentWebhookOutcome
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


# Retries whose provider answer a notification may still change.
ANSWERABLE_RETRY_OUTCOMES: frozenset[PaymentRetryOutcome] = frozenset(
    {
        PaymentRetryOutcome.CLAIMED,
        PaymentRetryOutcome.PROCESSING,
        PaymentRetryOutcome.APPROVED,
    }
)


def record_retry_outcome(
    retry_repo: PaymentRetryRepoContract,
    payment_order: PaymentOrderDocument,
    invoice: InvoiceDocument | None,
    notification: PaymentNotification,
    outcome: PaymentRetryOutcome,
    now: Microseconds,
) -> None:
    """
    The retry the notification answers records how it ended (a Flitt
    charge sent under the retry's id; for Stripe, the retries of the
    invoice still waiting for an answer), so the dunning job knows
    whether the card may be charged again.
    """

    retry_id: PaymentRetryId | None = parse_payment_retry_id(
        notification.order_reference
    )
    attempts: list[PaymentRetryAttemptDocument]
    if retry_id is not None:
        found = retry_repo.get(payment_order.business_id, retry_id)
        attempts = [] if found is None else [found]
    elif invoice is not None:
        attempts = retry_repo.list_for_invoice(payment_order.business_id, invoice.id)
    else:
        attempts = []

    for attempt in attempts:
        if attempt.outcome is outcome or (
            attempt.outcome not in ANSWERABLE_RETRY_OUTCOMES
        ):
            continue

        attempt.outcome = outcome
        attempt.updated_at = now
        retry_repo.save(attempt)


def settle_retried_invoice(
    invoice_repo: InvoiceRepoContract,
    invoice: InvoiceDocument,
    notification: PaymentNotification,
    now: Microseconds,
) -> InvoiceDocument | None:
    """
    The retried invoice is PAID with the retry's charge (its receipt).
    None when it is no longer open (paid another way, or by an earlier
    retry): the charge books nothing and is owed back.
    """

    if invoice.status not in OPEN_INVOICE_STATUSES:
        return None

    record_invoice_payment(invoice, InvoiceStatus.PAID, notification.card, now)
    if notification.payment_reference is not None:
        invoice.provider_reference = notification.payment_reference

    invoice.updated_at = now
    invoice_repo.save(invoice)
    return invoice


def settle_retry_approval(
    retry_repo: PaymentRetryRepoContract,
    invoice_repo: InvoiceRepoContract,
    payment_order: PaymentOrderDocument,
    retried: InvoiceDocument,
    notification: PaymentNotification,
    now: Microseconds,
) -> tuple[list[InvoiceDocument], PaymentWebhookOutcome]:
    """
    An approved retry: its row says so and it pays the invoice it retried.
    When that invoice is no longer open (another retry or the owner paid
    it first), the charge books nothing and is marked for refund.
    """

    record_retry_outcome(
        retry_repo,
        payment_order,
        retried,
        notification,
        PaymentRetryOutcome.APPROVED,
        now,
    )
    settled: InvoiceDocument | None = settle_retried_invoice(
        invoice_repo, retried, notification, now
    )
    if settled is None:
        payment_order.is_refund_due = True
        return [], PaymentWebhookOutcome.REFUND_DUE

    return [settled], PaymentWebhookOutcome.APPLIED
