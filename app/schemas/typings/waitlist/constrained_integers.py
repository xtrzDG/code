"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class WaitlistEntryCount(BaseConstrainedTypedInt):
    """How many waitlist entries (of one status, or in a period) a business has."""

    ge = 0


class WaitlistHoldMinutes(BaseConstrainedTypedInt):
    """
    How long a freed place offered to a waiting customer is kept for them
    before it goes to the next one: from a quarter of an hour to two hours.

    Example:
        hold = WaitlistHoldMinutes(30)
    """

    ge = 15
    le = 120


class WaitlistOfferCount(BaseConstrainedTypedInt):
    """How many freed places one waiting customer has been offered."""

    ge = 0


# Keep abc order for all non example types, if possible.
