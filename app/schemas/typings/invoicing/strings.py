"""Keep abc order."""

from base_typed_string import BaseTypedString


class BillingDocumentHtml(BaseTypedString):
    """
    The HTML an invoice or receipt PDF is laid out from; every value in it
    is escaped.
    """


class PaymentCardBrand(BaseTypedString):
    """
    Payment system of a card as the payment provider names it.

    Example:
        brand = PaymentCardBrand("VISA")
    """


# Keep abc order for all non example types, if possible.
