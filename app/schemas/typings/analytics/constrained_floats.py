"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class CohortPayingPercent(BaseConstrainedTypedFloat):
    """
    The share of a sign-up cohort with a paying business at the end of a
    month, in percent.

    Example:
        retained = CohortPayingPercent(37.5)
    """

    ge = 0.0
    le = 100.0


class ConversionPercent(BaseConstrainedTypedFloat):
    """
    The share of a group that reached a step (owners at a funnel step,
    trials that turned paid, businesses activated in a week), in percent.

    Example:
        trial_to_paid = ConversionPercent(42.86)
    """

    ge = 0.0
    le = 100.0


# Keep abc order for all non example types, if possible.
