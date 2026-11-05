"""
The error budgets of the product objectives (docs/operations/slo.md):
calls answered and notification delivery spend theirs by bad events,
voice latency and webhook lag by the days or hours over their target, a
window without data is not measured, booking success has no Prometheus
series, and the dashboard's "Product service levels" row runs exactly the
queries the monthly report runs.
"""

import json
import math
from pathlib import Path

import pytest

from app.schemas.constants.product_service_levels import ProductServiceLevel
from app.schemas.dto.product_service_levels import ProductBudgetView
from app.schemas.typings.observability.constrained_floats import (
    ServiceLevelObjective,
)
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.utilities.observability.product_service_levels import (
    CALLS_ANSWERED,
    LATENCY_OBJECTIVES,
    NOTIFICATION_DELIVERY,
    RATIO_OBJECTIVES,
    VOICE_LATENCY,
    WEBHOOK_LAG,
    count_of,
    latency_budget,
    measure_product_budgets,
    ratio_budget,
)
from app.utilities.observability.service_levels import budget_left_of

DASHBOARD: Path = (
    Path(__file__).resolve().parents[2] / "ops" / "grafana" / "workshop-service.json"
)


def left(budget: ProductBudgetView) -> int | None:
    value = budget.budget_left_permille
    return None if value is None else int(value)


@pytest.mark.parametrize(
    ("good", "bad", "expected"),
    [(995, 5, 500), (990, 10, 0), (980, 20, -1000), (1000, 0, 1000), (None, 3, -99000)],
)
def test_a_ratio_budget_is_spent_by_its_bad_events(
    good: int | None, bad: int, expected: int
) -> None:
    budget = ratio_budget(CALLS_ANSWERED, good, bad)

    assert left(budget) == expected
    assert int(budget.bad_events or 0) == bad
    assert int(budget.events or 0) == (good or 0) + bad
    assert budget.level is ProductServiceLevel.CALLS_ANSWERED


def test_a_ratio_objective_without_any_data_is_not_measured() -> None:
    budget = ratio_budget(NOTIFICATION_DELIVERY, None, None)

    assert budget.budget_left_permille is None
    assert budget.events is None


def test_a_latency_budget_is_spent_by_the_periods_over_its_target() -> None:
    # 5 % of 28 days is 1.4 days; 1 % of 672 hours is 6.72 hours.
    voice = latency_budget(VOICE_LATENCY, measured=20, over_target=1)
    lag = latency_budget(WEBHOOK_LAG, measured=672, over_target=7)
    calm = latency_budget(WEBHOOK_LAG, measured=300, over_target=None)

    assert left(voice) == 286
    assert (int(voice.periods or 0), int(voice.measured_periods or 0)) == (28, 20)
    assert int(voice.periods_over_target or 0) == 1
    assert left(lag) == -42
    assert left(calm) == 1000
    assert int(calm.periods_over_target or 0) == 0


def test_a_latency_window_without_data_is_not_measured() -> None:
    assert (
        latency_budget(VOICE_LATENCY, measured=None, over_target=None).periods is None
    )
    assert left(latency_budget(VOICE_LATENCY, measured=0, over_target=3)) is None


def test_broken_query_values_count_as_no_data() -> None:
    assert count_of(None) is None
    assert count_of(math.nan) is None
    assert count_of(-1.0) is None
    assert count_of(12.4) == 12


def test_the_shared_budget_arithmetic_never_counts_more_good_than_events() -> None:
    objective = ServiceLevelObjective(0.99)

    assert (
        int(
            budget_left_of(
                ServiceLevelEventCount(0), ServiceLevelEventCount(0), objective
            )
        )
        == 1000
    )
    assert (
        int(
            budget_left_of(
                ServiceLevelEventCount(10), ServiceLevelEventCount(12), objective
            )
        )
        == 1000
    )


def test_every_product_objective_is_reported_in_the_document_order() -> None:
    values = {
        CALLS_ANSWERED.good_query: 1990.0,
        CALLS_ANSWERED.bad_query: 10.0,
        NOTIFICATION_DELIVERY.good_query: 500.0,
        VOICE_LATENCY.measured_query: 28.0,
        WEBHOOK_LAG.measured_query: 600.0,
        WEBHOOK_LAG.over_target_query: 2.0,
    }
    asked: list[str] = []

    def query(expression: str) -> float | None:
        asked.append(expression)
        return values.get(expression)

    budgets = measure_product_budgets(query)

    assert [budget.level for budget in budgets] == [
        ProductServiceLevel.CALLS_ANSWERED,
        ProductServiceLevel.VOICE_LATENCY,
        ProductServiceLevel.BOOKING_SUCCESS,
        ProductServiceLevel.NOTIFICATION_DELIVERY,
        ProductServiceLevel.WEBHOOK_LAG,
    ]
    assert [left(budget) for budget in budgets] == [500, 1000, None, 1000, 702]
    assert float(budgets[2].objective) == 0.995
    assert len(asked) == len(set(asked)) == 8


def test_the_queries_name_each_objectives_target() -> None:
    assert "histogram_quantile(0.95," in VOICE_LATENCY.over_target_query
    assert f"> {float(VOICE_LATENCY.target):g})" in VOICE_LATENCY.over_target_query
    assert "[28d:1d]" in VOICE_LATENCY.over_target_query
    assert "histogram_quantile(0.99," in WEBHOOK_LAG.over_target_query
    assert f"> {float(WEBHOOK_LAG.target):g})" in WEBHOOK_LAG.over_target_query
    assert "[28d:1h]" in WEBHOOK_LAG.over_target_query
    assert 'route="/v1/voice/webhooks/conversation-initiation"' in (
        CALLS_ANSWERED.good_query
    )
    assert 'route="/v1/telephony/twilio/voice-fallback/{business_id}"' in (
        CALLS_ANSWERED.bad_query
    )


def test_the_dashboard_runs_the_reports_queries() -> None:
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    rows = [panel for panel in dashboard["panels"] if panel["type"] == "row"]
    expressions = " ".join(
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    )

    assert any(row["title"].startswith("Product service levels") for row in rows)
    for ratio in RATIO_OBJECTIVES:
        assert ratio.good_query in expressions, ratio.level
        assert ratio.bad_query in expressions, ratio.level
    for latency in LATENCY_OBJECTIVES:
        assert latency.over_target_query in expressions, latency.level
    assert "/ 0.01" in expressions
    assert "/ 1.4" in expressions
    assert "/ 6.72" in expressions
