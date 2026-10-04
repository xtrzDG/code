"""Invoicing: the VAT of an invoice, its printout and its PDF files."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.invoicing import BillingDocumentKind, TaxTreatment
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.invoicing.booleans import HasTaxpayerNumber
from app.schemas.typings.invoicing.constrained_integers import (
    BillingEmailCount,
    TaxRateBasisPoints,
)
from app.schemas.typings.invoicing.constrained_strings import BillingDocumentFileName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId


class TaxBuyer(ImmutableDTO):
    """
    The buyer as VAT sees it: where it is established and whether it gave
    a tax number (a business, for the reverse charge abroad).
    """

    country_code: CountryCode
    has_tax_id: HasTaxpayerNumber


class TaxDecision(ImmutableDTO):
    """How VAT applies to a buyer's invoices, and at which rate."""

    treatment: TaxTreatment
    rate_basis_points: TaxRateBasisPoints


class TaxedAmount(ImmutableDTO):
    """A price before tax, the tax on it and what is charged."""

    subtotal: Money
    tax: Money
    total: Money
    decision: TaxDecision


class BillingDocumentQuery(ImmutableDTO):
    """
    An owner downloads the invoice or the receipt of one invoice; the
    language defaults to the owner language of the business.
    """

    user_id: UserId
    business_id: BusinessId
    invoice_id: InvoiceId
    kind: BillingDocumentKind
    display_language: LanguageTag | None = None
    client_ip_address: ClientIpAddress | None = None


class BillingDocumentPrintout(ImmutableDTO):
    """
    One invoice to lay out as its invoice or its receipt: dates in the
    business's time zone, texts in `language` (English for a language the
    documents are not written in).
    """

    invoice: InvoiceDocument
    kind: BillingDocumentKind
    language: LanguageTag
    timezone: TimezoneName


class BillingDocumentFile(ImmutableDTO):
    """A rendered invoice or receipt: the PDF and the name to save it under."""

    file_name: BillingDocumentFileName
    content: bytes


class BillingDocumentEmailInput(ImmutableDTO):
    """The e-mail that carries a paid invoice and its receipt."""

    invoice: InvoiceDocument
    business_name: BusinessName
    language: LanguageTag
    timezone: TimezoneName


class BillingEmailsQueued(ImmutableDTO):
    """E-mails with invoice PDFs queued after one payment notification."""

    queued: BillingEmailCount
