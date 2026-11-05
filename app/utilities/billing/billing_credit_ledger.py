"""
The balance of a business's credit ledger and the line an invoice writes
when it uses credit.

Granted lines add, used lines take away, but only while their invoice
stands: an invoice voided since (a period billed again, a cancelled
subscription) gives its credit back without anyone writing a line. Each
currency has its own balance.
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingCreditKind, InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.typings.billing.constrained_integers import BillingCreditAmountMinor
from app.schemas.typings.billing.prefixed_id import BillingCreditId, InvoiceId
from app.schemas.typings.localization.constrained_strings import CurrencyCode

# Fixed namespace of the derived ids (never change it: stored ids depend on it).
USED_CREDIT_NAMESPACE: UUID = UUID("61a3a8ad-aaf8-4297-a121-1b37c94251dd")


def used_credit_id(invoice_id: InvoiceId) -> BillingCreditId:
    """The id of the line an invoice writes: one per invoice."""

    return BillingCreditId(uuid5(USED_CREDIT_NAMESPACE, str(invoice_id)))


def credit_balance(
    lines: Sequence[BillingCreditDocument],
    invoices: Sequence[InvoiceDocument],
    currency_code: CurrencyCode,
) -> int:
    """Credit granted in the currency minus what standing invoices used."""

    voided: set[InvoiceId] = {
        invoice.id for invoice in invoices if invoice.status is InvoiceStatus.VOID
    }
    balance: int = 0
    for line in lines:
        if line.currency_code != currency_code:
            continue

        if line.kind is BillingCreditKind.GRANTED:
            balance += int(line.amount_minor)
        elif line.invoice_id not in voided:
            balance -= int(line.amount_minor)

    return max(0, balance)


def used_credit_line(
    invoice: InvoiceDocument,
    amount_minor: int,
    now: Microseconds,
) -> BillingCreditDocument:
    """The ledger line of the credit an invoice used."""

    return BillingCreditDocument(
        id=used_credit_id(invoice.id),
        business_id=invoice.business_id,
        kind=BillingCreditKind.USED,
        amount_minor=BillingCreditAmountMinor(amount_minor),
        currency_code=invoice.currency_code,
        invoice_id=invoice.id,
        created_at=now,
        updated_at=now,
    )
