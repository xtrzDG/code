"""
The error budgets of the product objectives (docs/operations/slo.md,
"Product objectives") as the monthly SLO report reads them from Prometheus
(scripts/slo_report.py).
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.product_service_levels import ProductServiceLevel
from app.schemas.typings.observability.constrained_floats import (
    ServiceLevelObjective,
)
from app.schemas.typings.observability.constrained_integers import (
    ErrorBudgetLeftPermille,
    ServiceLevelEventCount,
    ServiceLevelPeriodCount,
)


class ProductBudgetView(ImmutableDTO):
    """
    One product objective over the last 28 days. A ratio objective counts
    its events and the bad ones; a latency objective counts the window's
    periods (days or hours), those with data, and those whose percentile
    missed the target.
    `budget_left_permille` is 1000 untouched, 0 spent, below 0 overspent,
    and None when Prometheus has no series for it (booking success) or did
    not answer.
    """

    level: ProductServiceLevel
    objective: ServiceLevelObjective
    events: ServiceLevelEventCount | None = None
    bad_events: ServiceLevelEventCount | None = None
    periods: ServiceLevelPeriodCount | None = None
    measured_periods: ServiceLevelPeriodCount | None = None
    periods_over_target: ServiceLevelPeriodCount | None = None
    budget_left_permille: ErrorBudgetLeftPermille | None = None
