"""
Texts of the invoice and receipt PDFs and the receipt e-mail in every
language whose texts are reviewed (English, Russian and Georgian; other
languages, Hebrew and German drafts among them, read English): an issued
document is kept as printed, so it never carries a draft. Placeholders in
braces are filled by the layout. The VAT notes want an accountant's sign-off before VAT
registration (docs/LAUNCH.md).
"""

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import reviewed_owner_text

INVOICE_TITLE = reviewed_owner_text("billing.document.invoice_title")
RECEIPT_TITLE = reviewed_owner_text("billing.document.receipt_title")
NUMBER = reviewed_owner_text("billing.document.number")
ISSUE_DATE = reviewed_owner_text("billing.document.issue_date")
PAYMENT_DATE = reviewed_owner_text("billing.document.payment_date")
SELLER = reviewed_owner_text("billing.document.seller")
BUYER = reviewed_owner_text("billing.document.buyer")
TAX_ID = reviewed_owner_text("billing.document.tax_id")
EMAIL = reviewed_owner_text("billing.document.email")
DESCRIPTION = reviewed_owner_text("billing.document.description")
PERIOD = reviewed_owner_text("billing.document.period")
AMOUNT = reviewed_owner_text("billing.document.amount")
SUBTOTAL = reviewed_owner_text("billing.document.subtotal")
VAT = reviewed_owner_text("billing.document.vat")
TOTAL_DUE = reviewed_owner_text("billing.document.total_due")
TOTAL_PAID = reviewed_owner_text("billing.document.total_paid")
AMOUNT_RECEIVED = reviewed_owner_text("billing.document.amount_received")
RECEIPT_NUMBER = reviewed_owner_text("billing.document.receipt_number")
PAYMENT_METHOD = reviewed_owner_text("billing.document.payment_method")
CARD_WITH_BRAND = reviewed_owner_text("billing.document.card_with_brand")
CARD_WITHOUT_BRAND = reviewed_owner_text("billing.document.card_without_brand")
CARD_UNKNOWN = reviewed_owner_text("billing.document.card_unknown")
DISCOUNT = reviewed_owner_text("billing.document.discount")
CREDIT_APPLIED = reviewed_owner_text("billing.document.credit_applied")
PAID_BY_BANK_TRANSFER = reviewed_owner_text("billing.document.paid_by_bank_transfer")
PAID_IN_CASH = reviewed_owner_text("billing.document.paid_in_cash")
PAID_BY_CREDIT = reviewed_owner_text("billing.document.paid_by_credit")
PAY_ONLINE = reviewed_owner_text("billing.document.pay_online")
RECEIPT_THANKS = reviewed_owner_text("billing.document.receipt_thanks")
GENERATED_BY = reviewed_owner_text("billing.document.generated_by")

RECEIPT_EMAIL_SUBJECT = reviewed_owner_text("billing.document.receipt_email_subject")
RECEIPT_EMAIL_BODY = reviewed_owner_text("billing.document.receipt_email_body")
RECEIPT_EMAIL_HINT = reviewed_owner_text("billing.document.receipt_email_hint")

STATUS_NAMES: dict[InvoiceStatus, LocalizedText] = {
    InvoiceStatus.ISSUED: reviewed_owner_text("billing.document.status_names.issued"),
    InvoiceStatus.PAID: reviewed_owner_text("billing.document.status_names.paid"),
    InvoiceStatus.FAILED: reviewed_owner_text("billing.document.status_names.failed"),
    InvoiceStatus.VOID: reviewed_owner_text("billing.document.status_names.void"),
}

TAX_NOTES: dict[TaxTreatment, LocalizedText] = {
    TaxTreatment.NOT_REGISTERED: reviewed_owner_text(
        "billing.document.tax_notes.not_registered"
    ),
    TaxTreatment.STANDARD: reviewed_owner_text("billing.document.tax_notes.standard"),
    TaxTreatment.REVERSE_CHARGE: reviewed_owner_text(
        "billing.document.tax_notes.reverse_charge"
    ),
    TaxTreatment.OUTSIDE_SCOPE: reviewed_owner_text(
        "billing.document.tax_notes.outside_scope"
    ),
}
