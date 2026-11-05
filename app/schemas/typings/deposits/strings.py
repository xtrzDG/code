"""Keep abc order."""

from base_typed_string import BaseTypedString


class DepositHoldEndText(BaseTypedString):
    """
    When a held place (or a banquet's payment link) lapses, in the
    business's time and the customer's language ("19:30", "Tue 14 Oct, 11:00").
    """


class DepositRefundDeadlineText(BaseTypedString):
    """
    The last moment a paid booking's cancellation still gets its deposit
    back (its start less the refund cutoff), in the business's time and the
    customer's language ("17:00", "Tue 14 Oct, 19:00").
    """


class DepositRefundTermsText(BaseTypedString):
    """
    The sentence of a deposit's line or reminder that tells the customer,
    before they pay, when a cancellation gets the deposit back and that a
    later one or a no-show keeps it, in the customer's language.
    """


class PaymentLinkHost(BaseTypedString):
    """The host of an owner's payment page, shown in the cabinet (pay.flitt.com)."""


class PaymentLinkPreview(BaseTypedString):
    """
    An owner's payment page as the cabinet shows it: the whole address, or,
    for one that carries a key, its host and path with the query hidden.
    """


# Keep abc order for all non example types, if possible.
