"""
The error budgets of the product objectives (docs/operations/slo.md,
"Product objectives") over the last 28 days of Prometheus series: the
queries, read by the dashboard's "Product service levels" row
(ops/grafana/workshop-service.json) and the monthly SLO report
(scripts/slo_report.py), and the arithmetic. Pure: the caller runs the
queries.

Two shapes of objective:

- A ratio objective (calls answered, notification delivery) counts its
  good and bad events; the budget is the share of bad events the objective
  allows, as for the answer and API budgets (service_levels.py).
- A latency objective (voice latency, webhook lag) counts the periods of
  the window (28 days, or 672 hours) whose percentile missed the target;
  the budget is the share of periods the objective allows (1.4 days,
  6.72 hours), as the answer latency budget counts the hours over 15 s.

Booking success has no Prometheus series: the tool results stored with
each reply are its only record, so its budget is not measured here.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.schemas.constants.product_service_levels import ProductServiceLevel
from app.schemas.dto.product_service_levels import ProductBudgetView
from app.schemas.typings.observability.constrained_floats import (
    ObservedSeconds,
    ServiceLevelObjective,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
    ServiceLevelPeriodCount,
)
from app.utilities.calls.twilio_voice_webhooks import (
    TWILIO_VOICE_FALLBACK_PATH_TEMPLATE,
)
from app.utilities.channels.channel_endpoints import (
    VOICE_CALL_INITIATION_PATH,
    VOICE_TOOL_PATH_TEMPLATE,
)
from app.utilities.observability.service_levels import budget_left_of

# Runs one instant PromQL query: its single value, or None without data.
type PrometheusQuery = Callable[[str], float | None]

WINDOW: str = "28d"
REQUESTS: str = "workshop_http_request_duration_seconds"


def route_requests(route: str) -> str:
    """POST requests one route template answered in the window, any status."""

    selector: str = f'{{method="POST", route="{route}"}}'
    return f"sum(increase({REQUESTS}_count{selector}[{WINDOW}]))"


@dataclass(frozen=True)
class RatioObjective:
    """Good events over good plus bad ones."""

    level: ProductServiceLevel
    objective: ServiceLevelObjective
    good_query: str
    bad_query: str


@dataclass(frozen=True)
class LatencyObjective:
    """Periods of the window whose percentile stayed under the target."""

    level: ProductServiceLevel
    objective: ServiceLevelObjective
    target: ObservedSeconds
    window_periods: ServiceLevelPeriodCount
    over_target_query: str
    measured_query: str


# Every call the voice platform takes asks the conversation-initiation
# webhook for its greeting (each agent is provisioned with it); a call it
# cannot take reaches the Twilio number's voice fallback.
CALLS_ANSWERED = RatioObjective(
    level=ProductServiceLevel.CALLS_ANSWERED,
    objective=ServiceLevelObjective(0.99),
    good_query=route_requests(VOICE_CALL_INITIATION_PATH),
    bad_query=route_requests(TWILIO_VOICE_FALLBACK_PATH_TEMPLATE),
)
# One delivered or dead attempt per settled outbox message; retries and
# deferred attempts are not settled yet.
NOTIFICATION_DELIVERY = RatioObjective(
    level=ProductServiceLevel.NOTIFICATION_DELIVERY,
    objective=ServiceLevelObjective(0.99),
    good_query=(
        "sum(increase(workshop_outbound_attempts_total"
        f'{{outcome="delivered"}}[{WINDOW}]))'
    ),
    bad_query=(
        f'sum(increase(workshop_outbound_attempts_total{{outcome="dead"}}[{WINDOW}]))'
    ),
)
VOICE_LATENCY = LatencyObjective(
    level=ProductServiceLevel.VOICE_LATENCY,
    objective=ServiceLevelObjective(0.95),
    target=ObservedSeconds(2.0),
    window_periods=ServiceLevelPeriodCount(28),
    over_target_query=(
        "count_over_time((histogram_quantile(0.95, sum by (le) (rate("
        f'{REQUESTS}_bucket{{method="POST", route="{VOICE_TOOL_PATH_TEMPLATE}"}}'
        f"[1d]))) > 2)[{WINDOW}:1d])"
    ),
    measured_query=(
        f"count_over_time((sum(rate({REQUESTS}_count"
        f'{{method="POST", route="{VOICE_TOOL_PATH_TEMPLATE}"}}[1d])) > 0)'
        f"[{WINDOW}:1d])"
    ),
)
WEBHOOK_LAG = LatencyObjective(
    level=ProductServiceLevel.WEBHOOK_LAG,
    objective=ServiceLevelObjective(0.99),
    target=ObservedSeconds(10.0),
    window_periods=ServiceLevelPeriodCount(28 * 24),
    over_target_query=(
        "count_over_time((histogram_quantile(0.99, sum by (le) (rate("
        'workshop_job_pickup_delay_seconds_bucket{lane="inbound"}[1h]))) > 10)'
        f"[{WINDOW}:1h])"
    ),
    measured_query=(
        "count_over_time((sum(rate(workshop_job_pickup_delay_seconds_count"
        f'{{lane="inbound"}}[1h])) > 0)[{WINDOW}:1h])'
    ),
)
RATIO_OBJECTIVES: tuple[RatioObjective, ...] = (CALLS_ANSWERED, NOTIFICATION_DELIVERY)
LATENCY_OBJECTIVES: tuple[LatencyObjective, ...] = (VOICE_LATENCY, WEBHOOK_LAG)
DOCUMENT_ORDER: tuple[ProductServiceLevel, ...] = (
    ProductServiceLevel.CALLS_ANSWERED,
    ProductServiceLevel.VOICE_LATENCY,
    ProductServiceLevel.BOOKING_SUCCESS,
    ProductServiceLevel.NOTIFICATION_DELIVERY,
    ProductServiceLevel.WEBHOOK_LAG,
)
# The objectives Prometheus has no series for, with their target.
UNMEASURED_OBJECTIVES: Mapping[ProductServiceLevel, ServiceLevelObjective] = {
    ProductServiceLevel.BOOKING_SUCCESS: ServiceLevelObjective(0.995),
}


def count_of(value: float | None) -> int | None:
    """A query's value as a count; None for no data or a broken value."""

    if value is None or not math.isfinite(value) or value < 0:
        return None

    return round(value)


def ratio_budget(
    objective: RatioObjective, good: int | None, bad: int | None
) -> ProductBudgetView:
    """A ratio objective's budget; unmeasured while both queries lack data."""

    if good is None and bad is None:
        return ProductBudgetView(level=objective.level, objective=objective.objective)

    bad_events = ServiceLevelEventCount(bad or 0)
    events = ServiceLevelEventCount((good or 0) + int(bad_events))
    return ProductBudgetView(
        level=objective.level,
        objective=objective.objective,
        events=events,
        bad_events=bad_events,
        budget_left_permille=budget_left_of(
            events,
            ServiceLevelEventCount(int(events) - int(bad_events)),
            objective.objective,
        ),
    )


def latency_budget(
    objective: LatencyObjective, measured: int | None, over_target: int | None
) -> ProductBudgetView:
    """
    A latency objective's budget over the window's periods; unmeasured
    while no period of the window has data. A period without data (no
    voice call that day) counts as within the target, and no period over
    it is an empty answer, not a missing one.
    """

    if not measured:
        return ProductBudgetView(level=objective.level, objective=objective.objective)

    periods: int = int(objective.window_periods)
    over = ServiceLevelPeriodCount(min(periods, over_target or 0))
    return ProductBudgetView(
        level=objective.level,
        objective=objective.objective,
        periods=objective.window_periods,
        measured_periods=ServiceLevelPeriodCount(min(periods, measured)),
        periods_over_target=over,
        budget_left_permille=budget_left_of(
            ServiceLevelEventCount(periods),
            ServiceLevelEventCount(periods - int(over)),
            objective.objective,
        ),
    )


def measure_product_budgets(query: PrometheusQuery) -> list[ProductBudgetView]:
    """Every product objective's budget, in the order of the SLO document."""

    budgets: dict[ProductServiceLevel, ProductBudgetView] = {}
    for ratio in RATIO_OBJECTIVES:
        budgets[ratio.level] = ratio_budget(
            ratio, count_of(query(ratio.good_query)), count_of(query(ratio.bad_query))
        )
    for latency in LATENCY_OBJECTIVES:
        budgets[latency.level] = latency_budget(
            latency,
            count_of(query(latency.measured_query)),
            count_of(query(latency.over_target_query)),
        )
    for level, objective in UNMEASURED_OBJECTIVES.items():
        budgets[level] = ProductBudgetView(level=level, objective=objective)

    return [budgets[level] for level in DOCUMENT_ORDER]
