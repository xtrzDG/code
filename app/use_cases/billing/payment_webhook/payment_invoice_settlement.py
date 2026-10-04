"""Mark the invoices a payment (or a declined payment) was for."""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.billing_profiles import PaymentCardSnapshot
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing_ledger import DueInvoicesRequest
from app.schemas.dto.payments import PaymentNotification
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.use_cases.shared.billing_records import (
    OPEN_INVOICE_STATUSES,
    find_next_period_start,
    is_superseded_period,
    list_subscription_invoices,
)
from app.use_cases.shared.invoice_payments import record_invoice_payment


def record_renewal_invoice(
    invoice_repo: InvoiceRepoContract,
    issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]],
    business: BusinessDocument,
    subscription: SubscriptionDocument,
    status: InvoiceStatus,
    payment_reference: PaymentProviderReference | None,
    now: Microseconds,
    *,
    charge: PaymentNotification | None = None,
) -> InvoiceDocument:
    """
    Invoice of the period an automatic charge (`charge`: the amount it
    took, which the invoice totals, and the card) was for. An invoice that
    already carries this provider payment is reused (a declined charge
    later approved becomes PAID), so a repeated delivery never bills a
    second period.
    """

    invoices: list[InvoiceDocument] = list_subscription_invoices(
        invoice_repo,
        subscription,
    )
    for invoice in invoices:
        if (
            payment_reference is None
            or invoice.kind is not InvoiceKind.SERVICE_PERIOD
            or invoice.provider_reference != payment_reference
        ):
            continue

        if status is InvoiceStatus.PAID and invoice.status in OPEN_INVOICE_STATUSES:
            record_invoice_payment(
                invoice,
                InvoiceStatus.PAID,
                None if charge is None else charge.card,
                now,
            )
            invoice.updated_at = now
            invoice_repo.save(invoice)

        return invoice

    return issue_due_invoices.run(
        DueInvoicesRequest(
            business=business,
            subscription=subscription,
            period_start=find_next_period_start(subscription, invoices),
            status=status,
            payment_reference=payment_reference,
            payment_card=None if charge is None else charge.card,
            charged_amount=None if charge is None else charge.amount,
        )
    )[-1]


def settle_order_invoices(
    invoice_repo: InvoiceRepoContract,
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
    status: InvoiceStatus,
    payment_reference: PaymentProviderReference | None,
    now: Microseconds,
    *,
    card: PaymentCardSnapshot | None = None,
) -> int:
    """
    Mark the checkout's invoices and return how many changed. A payment
    is money received, so an approved payment marks even a voided
    invoice as paid, except a service period another payment or a trial
    already covers (two checkout pages paid for nearly the same month,
    a page paid after the trial started): that one is voided instead,
    and so is every open period of the subscription the payment covers.
    A decline touches open invoices only.
    """

    paid_periods: list[InvoiceDocument] = [
        invoice
        for invoice in list_subscription_invoices(invoice_repo, subscription)
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status is InvoiceStatus.PAID
    ]
    changed_count: int = 0
    for invoice_id in payment_order.invoice_ids:
        invoice: InvoiceDocument | None = invoice_repo.get(
            payment_order.business_id,
            invoice_id,
        )
        if invoice is None or invoice.status is InvoiceStatus.PAID:
            continue

        if status is InvoiceStatus.FAILED and (
            invoice.status not in OPEN_INVOICE_STATUSES
        ):
            continue

        if status is InvoiceStatus.PAID and is_superseded_period(
            invoice, paid_periods, subscription
        ):
            void_open_invoice(invoice_repo, invoice, now)
            continue

        record_invoice_payment(invoice, status, card, now)
        if payment_reference is not None:
            invoice.provider_reference = payment_reference

        invoice.updated_at = now
        invoice_repo.save(invoice)
        changed_count += 1
        if status is InvoiceStatus.PAID and (
            invoice.kind is InvoiceKind.SERVICE_PERIOD
        ):
            paid_periods.append(invoice)

    if status is InvoiceStatus.PAID:
        for invoice in list_subscription_invoices(invoice_repo, subscription):
            if is_superseded_period(invoice, paid_periods, subscription):
                void_open_invoice(invoice_repo, invoice, now)

    return changed_count


def void_open_invoice(
    invoice_repo: InvoiceRepoContract,
    invoice: InvoiceDocument,
    now: Microseconds,
) -> None:
    """An open invoice nothing should collect any more becomes void."""

    if invoice.status not in OPEN_INVOICE_STATUSES:
        return

    invoice.status = InvoiceStatus.VOID
    invoice.updated_at = now
    invoice_repo.save(invoice)
