"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class DepositReference(BaseConstrainedTypedString):
    """
    The short code a deposit request is paid under, so staff match a
    payment in their merchant account to the booking (no look-alike letters).

    Example:
        reference = DepositReference("DK7Q3M9X")
    """

    min_length = 8
    max_length = 8
    pattern = r"^[ACDEFHJKLMNPQRTUVWXY3479]{8}$"


class PaymentLinkAddress(BaseConstrainedTypedString):
    """
    The owner's payment page as entered: an https address, either fixed or a
    template whose {amount}, {amount_minor}, {currency} and {reference} the
    platform fills (`payment_link_addresses` vets the rest).

    Example:
        page = PaymentLinkAddress("https://pay.example.com/d?sum={amount}")
    """

    min_length = 12
    max_length = 2048
    pattern = r"^https://[^\s/?#]+([/?#][^\s]*)?$"


class PaymentLinkAddressInput(BaseConstrainedTypedString):
    """
    A payment page as the owner typed it, before it is vetted (https, a
    public host, the placeholders) and becomes a `PaymentLinkAddress`.
    """

    min_length = 1
    max_length = 2048


class PaymentLinkLabel(BaseConstrainedTypedString):
    """The owner's name for one payment page ("Flitt, table deposit")."""

    min_length = 1
    max_length = 80
    pattern = r"\S"


class PaymentLinkUrl(BaseConstrainedTypedString):
    """
    The payment link one customer receives: the owner's page with the
    request's amount and reference filled in, https only.
    """

    min_length = 12
    max_length = 4096
    pattern = r"^https://[^\s/?#]+([/?#][^\s]*)?$"


# Keep abc order for all non example types, if possible.
