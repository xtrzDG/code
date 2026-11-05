"""Keep abc order."""

from base_typed_int import BaseTypedInt


class MrrChangeMinor(BaseTypedInt):
    """
    The net change of monthly recurring revenue over a period in euro
    cents: negative when churn and contraction outweigh the rest.

    Example:
        net_change = MrrChangeMinor(-4900)  # -49.00 EUR
    """


# Keep abc order for all non example types, if possible.
