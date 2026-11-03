"""
The product objectives' part of the monthly SLO report
(docs/operations/slo.md): what is left of each product error budget over
the last 28 days, read from Prometheus with the queries of the
dashboard's "Product service levels" row
(app/utilities/observability/product_service_levels.py).

    PROMETHEUS_URL=https://prometheus-prod-...grafana.net/api/prom \\
    PROMETHEUS_USER=<instance id> PROMETHEUS_TOKEN=<read token> \\
        uv run python -m scripts.slo_report [--json] [--out report.md]

PROMETHEUS_USER and PROMETHEUS_TOKEN are Grafana Cloud's basic auth (a
token alone is sent as a bearer token; neither for a local Prometheus).
The three main budgets come from /admin/system (GET
/v1/admin/system/error-budget); booking success has no Prometheus series
and is reported as not measured. Exit 0 with the report, 1 when a budget
is spent, 2 without PROMETHEUS_URL or when Prometheus does not answer.
"""

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO, cast

import httpx

from app.schemas.dto.product_service_levels import ProductBudgetView
from app.utilities.observability.product_service_levels import (
    measure_product_budgets,
)

EXIT_OK: int = 0
EXIT_SPENT: int = 1
EXIT_UNREACHABLE: int = 2
TIMEOUT_SECONDS: float = 30.0
TITLES: Mapping[str, str] = {
    "calls_answered": "Calls answered",
    "voice_latency": "Voice latency (tool p95 under 2 s, per day)",
    "booking_success": "Booking success",
    "notification_delivery": "Notification delivery",
    "webhook_lag": "Webhook lag (inbound pickup p99 under 10 s, per hour)",
}
PERIOD_NAMES: Mapping[str, str] = {"voice_latency": "days", "webhook_lag": "hours"}


class PrometheusError(Exception):
    """Prometheus refused a query or answered something else."""


def read_value(payload: object) -> float | None:
    """The value of an instant query's single sample; None without one."""

    body = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
    if body.get("status") != "success":
        raise PrometheusError(str(body.get("error", "no success status")))

    result = cast(list[Any], cast(dict[str, Any], body.get("data") or {}).get("result"))
    if not result:
        return None

    sample = cast(dict[str, Any], result[0])
    return float(cast(list[Any], sample["value"])[1])


def build_client(
    environment: Mapping[str, str], transport: httpx.BaseTransport | None
) -> httpx.Client:
    user = environment.get("PROMETHEUS_USER", "").strip()
    token = environment.get("PROMETHEUS_TOKEN", "").strip()
    headers: dict[str, str] = {"Accept": "application/json"}
    if token and not user:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(
        base_url=environment["PROMETHEUS_URL"].strip().rstrip("/"),
        auth=(user, token) if user and token else None,
        headers=headers,
        timeout=TIMEOUT_SECONDS,
        transport=transport,
    )


def describe(budget: ProductBudgetView) -> str:
    level = str(budget.level)
    if budget.budget_left_permille is None:
        what = (
            "not in Prometheus: count the booking tool results of the replies"
            if level == "booking_success"
            else "no data in the window"
        )
        return f"| {TITLES[level]} | {float(budget.objective):.1%} | {what} | |"

    if budget.events is not None:
        seen = f"{int(budget.bad_events or 0):,} bad of {int(budget.events):,}"
    else:
        seen = (
            f"{int(budget.periods_over_target or 0)} of "
            f"{int(budget.periods or 0)} {PERIOD_NAMES[level]} over the target "
            f"({int(budget.measured_periods or 0)} with data)"
        )
    left = int(budget.budget_left_permille) / 10
    flag = " **spent**" if left <= 0 else ""
    target = f"{float(budget.objective):.1%}"
    return f"| {TITLES[level]} | {target} | {seen} | {left:.1f}%{flag} |"


def to_markdown(budgets: Sequence[ProductBudgetView]) -> str:
    lines = [
        "### Product error budgets (28 days, Prometheus)",
        "",
        "| Objective | Target | Measured | Budget left |",
        "| --- | --- | --- | --- |",
        *(describe(budget) for budget in budgets),
        "",
        "Calls answered counts the calls that asked for their greeting over "
        "those plus the calls that reached the Twilio voice fallback.",
    ]
    return "\n".join(lines) + "\n"


def run(
    arguments: Sequence[str],
    environment: Mapping[str, str],
    output: TextIO,
    transport: httpx.BaseTransport | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.slo_report")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--out", type=Path, help="also write the report here")
    options = parser.parse_args(arguments)
    if not environment.get("PROMETHEUS_URL", "").strip():
        output.write("PROMETHEUS_URL is not set: nothing to read.\n")
        return EXIT_UNREACHABLE

    with build_client(environment, transport) as client:

        def query(expression: str) -> float | None:
            response = client.get("/api/v1/query", params={"query": expression})
            response.raise_for_status()
            return read_value(response.json())

        try:
            budgets = measure_product_budgets(query)
        except (httpx.HTTPError, PrometheusError, ValueError, KeyError) as error:
            output.write(f"Prometheus did not answer: {error}\n")
            return EXIT_UNREACHABLE

    report = (
        json.dumps([budget.model_dump(mode="json") for budget in budgets], indent=2)
        + "\n"
        if options.json
        else to_markdown(budgets)
    )
    output.write(report)
    if options.out is not None:
        options.out.write_text(report, encoding="utf-8")
    spent = [
        budget
        for budget in budgets
        if budget.budget_left_permille is not None
        and int(budget.budget_left_permille) <= 0
    ]
    return EXIT_SPENT if spent else EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:], os.environ, sys.stdout))


if __name__ == "__main__":
    main()
