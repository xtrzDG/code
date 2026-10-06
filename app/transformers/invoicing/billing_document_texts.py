"""
Texts of the invoice and receipt PDFs in English, Russian and Georgian
(other languages read English). Placeholders in braces are filled by the
layout. The VAT notes want an accountant's sign-off before VAT
registration (docs/LAUNCH.md).
"""

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

INVOICE_TITLE = owner_text("billing.document.invoice_title")
RECEIPT_TITLE = owner_text("billing.document.receipt_title")
NUMBER = owner_text("billing.document.number")
ISSUE_DATE = owner_text("billing.document.issue_date")
PAYMENT_DATE = owner_text("billing.document.payment_date")
SELLER = owner_text("billing.document.seller")
BUYER = owner_text("billing.document.buyer")
TAX_ID = owner_text("billing.document.tax_id")
EMAIL = owner_text("billing.document.email")
DESCRIPTION = owner_text("billing.document.description")
PERIOD = owner_text("billing.document.period")
AMOUNT = owner_text("billing.document.amount")
SUBTOTAL = owner_text("billing.document.subtotal")
VAT = owner_text("billing.document.vat")
TOTAL_DUE = owner_text("billing.document.total_due")
TOTAL_PAID = owner_text("billing.document.total_paid")
AMOUNT_RECEIVED = owner_text("billing.document.amount_received")
RECEIPT_NUMBER = owner_text("billing.document.receipt_number")
PAYMENT_METHOD = owner_text("billing.document.payment_method")
CARD_WITH_BRAND = owner_text("billing.document.card_with_brand")
CARD_WITHOUT_BRAND = owner_text("billing.document.card_without_brand")
CARD_UNKNOWN = owner_text("billing.document.card_unknown")
DISCOUNT = owner_text("billing.document.discount")
CREDIT_APPLIED = owner_text("billing.document.credit_applied")
PAID_BY_BANK_TRANSFER = owner_text("billing.document.paid_by_bank_transfer")
PAID_IN_CASH = owner_text("billing.document.paid_in_cash")
PAID_BY_CREDIT = owner_text("billing.document.paid_by_credit")
PAY_ONLINE = owner_text("billing.document.pay_online")
RECEIPT_THANKS = owner_text("billing.document.receipt_thanks")
GENERATED_BY = owner_text("billing.document.generated_by")

RECEIPT_EMAIL_SUBJECT = owner_text("billing.document.receipt_email_subject")
RECEIPT_EMAIL_BODY = owner_text("billing.document.receipt_email_body")
RECEIPT_EMAIL_HINT = owner_text("billing.document.receipt_email_hint")

STATUS_NAMES: dict[InvoiceStatus, LocalizedText] = {
    InvoiceStatus.ISSUED: owner_text("billing.document.status_names.issued"),
    InvoiceStatus.PAID: owner_text("billing.document.status_names.paid"),
    InvoiceStatus.FAILED: owner_text("billing.document.status_names.failed"),
    InvoiceStatus.VOID: owner_text("billing.document.status_names.void"),
}

TAX_NOTES: dict[TaxTreatment, LocalizedText] = {
    TaxTreatment.NOT_REGISTERED: owner_text(
        "billing.document.tax_notes.not_registered"
    ),
    TaxTreatment.STANDARD: owner_text("billing.document.tax_notes.standard"),
    TaxTreatment.REVERSE_CHARGE: owner_text(
        "billing.document.tax_notes.reverse_charge"
    ),
    TaxTreatment.OUTSIDE_SCOPE: owner_text("billing.document.tax_notes.outside_scope"),
}
