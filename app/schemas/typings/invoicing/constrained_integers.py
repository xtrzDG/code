"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class InvoiceSequenceNumber(BaseConstrainedTypedInt):
    """
    Place of an invoice in its series and year: 1 for the first invoice of
    the year, then one more for each invoice, without gaps.

    Example:
        forty_second = InvoiceSequenceNumber(42)
    """

    ge = 1


class InvoiceYear(BaseConstrainedTypedInt):
    """
    Calendar year (in the seller's time zone) an invoice number counts in.

    Example:
        year = InvoiceYear(2026)
    """

    ge = 2000
    le = 9999


class TaxRateBasisPoints(BaseConstrainedTypedInt):
    """
    A tax rate in hundredths of a percent, so rates stay exact integers:
    1800 is 18 %, 0 is no tax.

    Example:
        georgian_vat = TaxRateBasisPoints(1800)
    """

    ge = 0
    le = 10_000


# Keep abc order for all non example types, if possible.
