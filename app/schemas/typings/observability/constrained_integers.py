"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BurnRatePercent(BaseConstrainedTypedInt):
    """
    How fast an error budget burns, in percent of the pace that would spend
    it exactly over the objective's 28 days: 100 spends it on the last day,
    1440 (14.4 times) in under two days.
    """

    ge = 0
    le = 100_000_000


class ErrorBudgetLeftPermille(BaseConstrainedTypedInt):
    """
    What is left of an error budget over the last 28 days, in tenths of a
    percent of the budget: 1000 is untouched, 0 spent, below 0 overspent
    (down to -100 times the budget).
    """

    ge = -100_000
    le = 1000


class HttpStatusCode(BaseConstrainedTypedInt):
    """The status code an HTTP response was answered with."""

    ge = 100
    le = 599


class MetricsPort(BaseConstrainedTypedInt):
    """The TCP port the worker serves its /metrics on (WORKER_METRICS_PORT)."""

    ge = 1024
    le = 65535


class ServiceLevelEventCount(BaseConstrainedTypedInt):
    """
    Events of one service level indicator in a window: customer messages
    that arrived, or API requests answered, and how many of them were good.
    """

    ge = 0
    le = 1_000_000_000_000


# Keep abc order for all non example types, if possible.
