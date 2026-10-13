"""Keep abc order."""

from base_typed_string import BaseTypedString


class DepositHoldEndText(BaseTypedString):
    """
    When a held place (or a banquet's payment link) lapses, in the
    business's time and the customer's language ("19:30", "Tue 14 Oct, 11:00").
    """


class PaymentLinkHost(BaseTypedString):
    """The host of an owner's payment page, shown in the cabinet (pay.flitt.com)."""


class PaymentLinkPreview(BaseTypedString):
    """
    An owner's payment page as the cabinet shows it: the whole address, or,
    for one that carries a key, its host and path with the query hidden.
    """


# Keep abc order for all non example types, if possible.
