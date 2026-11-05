"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CommissionMonth(BaseConstrainedTypedString):
    """
    The calendar month (UTC) a partner's commission was earned in and is
    paid out with, as YYYY-MM.

    Example:
        month = CommissionMonth("2026-10")
    """

    min_length = 7
    max_length = 7
    pattern = r"^\d{4}-(0[1-9]|1[0-2])$"


class PartnerName(BaseConstrainedTypedString):
    """
    The name of a partner as the platform team and the partner see it (an
    agency, a consultant).

    Example:
        name = PartnerName("Tbilisi Digital Agency")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[^\x00-\x1f\x7f<>]*\S[^\x00-\x1f\x7f<>]*$"


class PayoutReference(BaseConstrainedTypedString):
    """
    How the platform team paid a partner's commissions out (the bank
    transfer's reference), written down when it marks them paid.

    Example:
        reference = PayoutReference("TBC transfer 2026-11-03 #88123")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[^\x00-\x1f\x7f<>]*\S[^\x00-\x1f\x7f<>]*$"


class ReferralLink(BaseConstrainedTypedString):
    """
    A link to the platform's site that carries a referral code (`?ref=`)
    and where it was shown (`&src=`): an owner's invitation, a partner's
    link, the "Powered by" link of a chat or a table card.

    Example:
        link = ReferralLink("https://app.example.com/?ref=k3q7m2x9pa&src=powered_by")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/?#]+(/[^\s]*)?$"


# Keep abc order for all non example types, if possible.
