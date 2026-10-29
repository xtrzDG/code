"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class AverageVisitScore(BaseConstrainedTypedFloat):
    """
    The mean of the customers' visit ratings over a period (1 to 5).

    Example:
        average = AverageVisitScore(4.6)
    """

    ge = 1.0
    le = 5.0


# Keep abc order for all non example types, if possible.
