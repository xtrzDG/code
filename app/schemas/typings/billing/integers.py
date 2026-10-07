"""Keep abc order."""

from base_typed_int import BaseTypedInt


class MarginAmountMinor(BaseTypedInt):
    """
    Revenue minus provider cost in minor units of a currency; negative for a
    loss, so it has no lower bound.

    Example:
        monthly_margin = MarginAmountMinor(12010)  # 120.10 EUR
    """


# Keep abc order for all non example types, if possible.
