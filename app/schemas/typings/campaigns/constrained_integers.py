"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CampaignMessageCount(BaseConstrainedTypedInt):
    """How many campaign messages (of one status, or in a period) a business sent."""

    ge = 0


class CampaignMonthlyCap(BaseConstrainedTypedInt):
    """
    The most campaign messages one business sends in a calendar month of
    its time zone (a brake on cost and on annoying customers).

    Example:
        cap = CampaignMonthlyCap(100)
    """

    ge = 1
    le = 2000


class RebookingDelayDays(BaseConstrainedTypedInt):
    """
    The days of a rebooking rule: after a customer's last visit for an
    invitation back or a recall (5 weeks for a salon, half a year for a
    clinic), or before an arrival for the note ahead of it.

    Example:
        delay = RebookingDelayDays(35)
    """

    ge = 1
    le = 730


# Keep abc order for all non example types, if possible.
