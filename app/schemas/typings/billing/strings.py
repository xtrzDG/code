"""Keep abc order."""

from base_typed_string import BaseTypedString


class InvoiceDescription(BaseTypedString):
    """
    Invoice line text. Always a service ("call and message handling service"),
    never a "license" or "consultation" (concept: tax rules).
    """


class PaymentProviderReference(BaseTypedString):
    """Identifier of a subscription or payment at the payment provider."""


# Keep abc order for all non example types, if possible.
