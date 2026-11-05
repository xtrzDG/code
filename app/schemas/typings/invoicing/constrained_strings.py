"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class BillingAddressText(BaseConstrainedTypedString):
    """
    Postal address an invoice names for its buyer or seller, as the owner
    wrote it (up to six lines).

    Example:
        address = BillingAddressText("12 Rustaveli Ave\\n0108 Tbilisi")
    """

    min_length = 3
    max_length = 400
    pattern = r"^[^\x00-\x09\x0b-\x1f\x7f]+$"


class BillingDocumentFileName(BaseConstrainedTypedString):
    """
    File name of an invoice or receipt PDF: Latin letters, digits, dots,
    dashes and underscores only, so every mail client and file system
    keeps it as it is.

    Example:
        file_name = BillingDocumentFileName("invoice-AW-2026-000042.pdf")
    """

    min_length = 5
    max_length = 120
    pattern = r"^[A-Za-z0-9][A-Za-z0-9._\-]*\.pdf$"


class BillingLegalName(BaseConstrainedTypedString):
    """
    Registered name of a company or sole trader on invoices.

    Example:
        legal_name = BillingLegalName("Mtsvane Ezo LLC")
    """

    min_length = 1
    max_length = 200
    pattern = r"^[^\x00-\x1f\x7f]+$"


class InvoiceCounterKey(BaseConstrainedTypedString):
    """
    Storage key of one yearly invoice counter: the series and the year.

    Example:
        key = InvoiceCounterKey("AW:2026")
    """

    min_length = 6
    max_length = 15
    pattern = r"^[A-Z0-9]{1,10}:[0-9]{4}$"


class InvoiceNumber(BaseConstrainedTypedString):
    """
    Number of an invoice: its series, the year and its place in the year,
    six digits at least.

    Example:
        number = InvoiceNumber("AW-2026-000042")
    """

    min_length = 13
    max_length = 30
    pattern = r"^[A-Z0-9]{1,10}-[0-9]{4}-[0-9]{6,12}$"


class InvoiceSeries(BaseConstrainedTypedString):
    """
    Prefix of the seller's invoice numbers (SELLER_INVOICE_SERIES).

    Example:
        series = InvoiceSeries("AW")
    """

    min_length = 1
    max_length = 10
    pattern = r"^[A-Z0-9]{1,10}$"


class PaymentCardLastDigits(BaseConstrainedTypedString):
    """
    The last four digits of the card a payment was made with, the only
    part of a card number ever stored.

    Example:
        last_digits = PaymentCardLastDigits("4242")
    """

    min_length = 4
    max_length = 4
    pattern = r"^[0-9]{4}$"


class TaxpayerIdentificationNumber(BaseConstrainedTypedString):
    """
    A company's or sole trader's tax number as its tax office writes it
    (Georgia: 9 or 11 digits; EU VAT numbers start with the country code).
    Letters, digits, spaces, dots, slashes and dashes.

    Example:
        tax_id = TaxpayerIdentificationNumber("405123456")
    """

    min_length = 2
    max_length = 40
    pattern = r"^[A-Za-z0-9](?:[A-Za-z0-9 ./\-]*[A-Za-z0-9])?$"


# Keep abc order for all non example types, if possible.
