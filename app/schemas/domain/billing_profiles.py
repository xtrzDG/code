from base_pydantic_schemas import BaseDocument, PersistentDocument

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.invoicing.constrained_integers import (
    InvoiceSequenceNumber,
    InvoiceYear,
)
from app.schemas.typings.invoicing.constrained_strings import (
    BillingAddressText,
    BillingLegalName,
    InvoiceCounterKey,
    InvoiceSeries,
    PaymentCardLastDigits,
    TaxpayerIdentificationNumber,
)
from app.schemas.typings.invoicing.prefixed_id import BillingProfileId
from app.schemas.typings.invoicing.strings import PaymentCardBrand
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId


class BillingProfileDocument(BaseDocument):
    """
    The details a business wants on its invoices (concept: the accountant's
    "реквизиты"): the registered name, the tax number, the postal address,
    the e-mail invoices and receipts go to, and the country (which decides
    the VAT). One per business (the id derives from it); without one,
    invoices name the business and its country.
    """

    id: BillingProfileId
    business_id: BusinessId
    legal_name: BillingLegalName
    tax_id: TaxpayerIdentificationNumber | None = None
    address: BillingAddressText | None = None
    billing_email: EmailAddress | None = None
    country_code: CountryCode
    updated_by: UserId | None = None


class InvoiceCounterDocument(BaseDocument):
    """
    The last number given in one invoice series and year (a platform
    collection: the seller numbers every business's invoices in one row).
    A new number is taken by compare-and-set on `last_number`, so two
    processes never hand out the same one and none is skipped.
    """

    id: InvoiceCounterKey
    series: InvoiceSeries
    year: InvoiceYear
    last_number: InvoiceSequenceNumber


class InvoiceParty(PersistentDocument):
    """
    The seller or the buyer as an invoice names them, copied when it is
    issued: later changes of the billing details never rewrite an invoice.
    """

    legal_name: BillingLegalName
    tax_id: TaxpayerIdentificationNumber | None = None
    address: BillingAddressText | None = None
    email: EmailAddress | None = None
    country_code: CountryCode


class PaymentCardSnapshot(PersistentDocument):
    """
    The card an invoice was paid with, masked as the payment provider
    reported it: the payment system and the last four digits, never more.
    """

    brand: PaymentCardBrand | None = None
    last_digits: PaymentCardLastDigits | None = None
