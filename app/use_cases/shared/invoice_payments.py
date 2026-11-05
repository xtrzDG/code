"""What an invoice records when a payment settles or fails it."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_profiles import PaymentCardSnapshot


def record_invoice_payment(
    invoice: InvoiceDocument,
    status: InvoiceStatus,
    card: PaymentCardSnapshot | None,
    now: Microseconds,
) -> None:
    """
    Give the invoice the payment's status; a PAID one also records when
    (the receipt's date) and, when the provider said, the masked card.
    """

    invoice.status = status
    if status is not InvoiceStatus.PAID:
        return

    invoice.paid_at = now
    if card is not None:
        invoice.payment_card = card
