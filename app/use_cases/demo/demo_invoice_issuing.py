"""
The demo's paid invoices: numbered, with their parties and VAT, as a
payment issues a real one (an open invoice stays as the catalog built it).
"""

from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money


def issue_demo_invoice_if_paid(
    invoice_issuing: InvoiceIssuingFacilitatorContract,
    business: BusinessDocument,
    invoice: InvoiceDocument,
) -> InvoiceDocument:
    """The invoice as stored: issued for the amount charged when it is paid."""

    if invoice.status is not InvoiceStatus.PAID:
        return invoice

    charged: Money = Money(
        amount_minor=invoice.amount_minor, currency_code=invoice.currency_code
    )
    return invoice_issuing.issue(business, invoice, charged=charged)
