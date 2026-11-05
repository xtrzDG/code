"""
scripts/slo_report.py: the product budgets of the monthly SLO report from
Prometheus' query API, with Grafana Cloud's basic auth or a bearer token;
exit 1 when a budget is spent, 2 without Prometheus.
"""

import io
import json
from pathlib import Path

import httpx

from app.utilities.observability.product_service_levels import (
    CALLS_ANSWERED,
    NOTIFICATION_DELIVERY,
    VOICE_LATENCY,
    WEBHOOK_LAG,
)
from scripts.slo_report import run

URL: str = "https://prometheus.example.test/api/prom"


def prometheus(
    values: dict[str, float], seen: list[httpx.Request] | None = None
) -> httpx.MockTransport:
    def answer(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        assert request.url.path == "/api/prom/api/v1/query"
        expression = request.url.params["query"]
        result: list[dict[str, object]] = (
            [{"metric": {}, "value": [1.0, str(values[expression])]}]
            if expression in values
            else []
        )
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"resultType": "vector", "result": result},
            },
        )

    return httpx.MockTransport(answer)


HEALTHY: dict[str, float] = {
    CALLS_ANSWERED.good_query: 995.0,
    CALLS_ANSWERED.bad_query: 5.0,
    NOTIFICATION_DELIVERY.good_query: 2000.0,
    NOTIFICATION_DELIVERY.bad_query: 4.0,
    VOICE_LATENCY.measured_query: 28.0,
    WEBHOOK_LAG.measured_query: 650.0,
    WEBHOOK_LAG.over_target_query: 1.0,
}


def test_the_report_lists_every_product_budget() -> None:
    output = io.StringIO()

    code = run([], {"PROMETHEUS_URL": URL}, output, prometheus(HEALTHY))

    report = output.getvalue()
    assert code == 0, report
    assert "| Calls answered | 99.0% | 5 bad of 1,000 | 50.0% |" in report
    assert "| Notification delivery | 99.0% | 4 bad of 2,004 | 80.0% |" in report
    assert "0 of 28 days over the target (28 with data) | 100.0% |" in report
    assert "1 of 672 hours over the target (650 with data) | 85.1% |" in report
    assert "| Booking success | 99.5% | not in Prometheus" in report


def test_a_spent_budget_fails_the_run_and_json_is_written(tmp_path: Path) -> None:
    output = io.StringIO()
    spent = HEALTHY | {CALLS_ANSWERED.bad_query: 50.0}
    out = tmp_path / "report.json"

    code = run(
        ["--json", "--out", str(out)],
        {"PROMETHEUS_URL": URL},
        output,
        prometheus(spent),
    )

    assert code == 1
    budgets = json.loads(out.read_text(encoding="utf-8"))
    assert budgets[0]["level"] == "calls_answered"
    assert budgets[0]["budget_left_permille"] < 0
    assert budgets[2]["budget_left_permille"] is None


def test_grafana_cloud_basic_auth_or_a_bearer_token_is_sent() -> None:
    seen: list[httpx.Request] = []
    run(
        [],
        {"PROMETHEUS_URL": URL, "PROMETHEUS_USER": "1234", "PROMETHEUS_TOKEN": "t0k"},
        io.StringIO(),
        prometheus(HEALTHY, seen),
    )
    run(
        [],
        {"PROMETHEUS_URL": URL + "/", "PROMETHEUS_TOKEN": "t0k"},
        io.StringIO(),
        prometheus(HEALTHY, seen),
    )

    assert seen[0].headers["Authorization"].startswith("Basic ")
    assert seen[-1].headers["Authorization"] == "Bearer t0k"


def test_without_prometheus_nothing_is_reported() -> None:
    output = io.StringIO()

    assert run([], {}, output) == 2
    assert "PROMETHEUS_URL is not set" in output.getvalue()

    def refuse(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"status": "error", "error": "bad query"})

    refused = io.StringIO()
    code = run([], {"PROMETHEUS_URL": URL}, refused, httpx.MockTransport(refuse))

    assert code == 2
    assert "Prometheus did not answer: bad query" in refused.getvalue()


def test_a_token_never_travels_over_plain_http() -> None:
    seen: list[httpx.Request] = []
    output = io.StringIO()
    remote = {
        "PROMETHEUS_URL": "http://prometheus.example.test",
        "PROMETHEUS_TOKEN": "t0k",
    }

    assert run([], remote, output, prometheus(HEALTHY, seen)) == 2
    assert "only over https" in output.getvalue()
    assert seen == []

    local = {
        "PROMETHEUS_URL": "http://localhost:9090/api/prom",
        "PROMETHEUS_TOKEN": "t0k",
    }
    assert run([], local, io.StringIO(), prometheus(HEALTHY, seen)) == 0
    assert seen[-1].headers["Authorization"] == "Bearer t0k"
