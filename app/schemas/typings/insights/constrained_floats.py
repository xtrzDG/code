"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class AfterHoursSharePercent(BaseConstrainedTypedFloat):
    """
    Share of conversations that started outside opening hours, in percent.

    Example:
        share = AfterHoursSharePercent(37.5)
    """

    ge = 0.0
    le = 100.0


# Keep abc order for all non example types, if possible.
