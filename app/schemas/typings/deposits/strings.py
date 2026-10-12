"""Keep abc order."""

from base_typed_string import BaseTypedString


class PaymentLinkHost(BaseTypedString):
    """The host of an owner's payment page, shown in the cabinet (pay.flitt.com)."""


class PaymentLinkLabel(BaseTypedString):
    """The owner's name for one payment page ("Flitt, table deposit")."""


class PaymentLinkPreview(BaseTypedString):
    """
    An owner's payment page as the cabinet shows it: the whole address, or,
    for one that carries a key, its host and path with the query hidden.
    """


# Keep abc order for all non example types, if possible.
