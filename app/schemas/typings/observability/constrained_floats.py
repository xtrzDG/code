"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class ObservedSeconds(BaseConstrainedTypedFloat):
    """
    A measured duration in seconds for a metric (a request, a model call,
    a wait for a database connection); never negative.
    """

    ge = 0.0
    le = 31_536_000.0


class ServiceLevelObjective(BaseConstrainedTypedFloat):
    """
    The share of events an objective promises to get right over 28 days,
    e.g. 0.995 of customer messages answered within 60 s; the rest
    (1 - objective) is the error budget.
    """

    gt = 0.0
    lt = 1.0


# Keep abc order for all non example types, if possible.
