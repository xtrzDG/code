"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class StatusCheckCount(BaseConstrainedTypedInt):
    """
    How many times the status of a component was recorded on a day, or
    how many of those records found it in a given state.
    """

    ge = 0


# Keep abc order for all non example types, if possible.
