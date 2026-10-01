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


class PaymentFailureReason(BaseTypedString):
    """Reason a payment provider gave for a declined payment (no card data)."""


class PaymentNotificationKey(BaseTypedString):
    """
    Idempotency key of one provider notification: payment reference and status.

    Example:
        key = PaymentNotificationKey("802345671:approved")
    """


class PaymentProviderReference(BaseTypedString):
    """Identifier of a subscription or payment at the payment provider."""


class PaymentWebhookBody(BaseTypedString):
    """Raw body of a payment provider notification, before verification."""


class PaymentWebhookContentType(BaseTypedString):
    """Content-Type header of a payment provider notification."""


# Keep abc order for all non example types, if possible.
