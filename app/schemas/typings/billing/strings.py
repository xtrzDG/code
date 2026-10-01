"""Keep abc order."""

from base_typed_string import BaseTypedString


class ExchangeRateSourceName(BaseTypedString):
    """
    Who published an exchange rate, e.g. "National Bank of Georgia".

    Example:
        source = ExchangeRateSourceName("National Bank of Georgia")
    """


class InvoiceDescription(BaseTypedString):
    """
    Invoice line text. Always a service ("call and message handling service"),
    never a "license" or "consultation" (concept: tax rules).
    """


class PaymentProviderReference(BaseTypedString):
    """Identifier of a subscription or payment at the payment provider."""


# Keep abc order for all non example types, if possible.
