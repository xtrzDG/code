"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CommissionInvoiceCount(BaseConstrainedTypedInt):
    """
    How many paid invoices earned a partner commissions (in one currency
    and status, or marked paid in one payout).

    Example:
        invoices = CommissionInvoiceCount(4)
    """

    ge = 0


class CommissionRateBasisPoints(BaseConstrainedTypedInt):
    """
    A partner's share of what the businesses they brought pay, in
    hundredths of a percent before tax (0 to 50 %).

    Example:
        twenty_percent = CommissionRateBasisPoints(2000)
    """

    ge = 0
    le = 5000


class ReferredBusinessCount(BaseConstrainedTypedInt):
    """
    How many businesses signed up by a code (all of them, or those that
    paid, or those whose referral was rewarded).

    Example:
        joined = ReferredBusinessCount(3)
    """

    ge = 0


# Keep abc order for all non example types, if possible.
