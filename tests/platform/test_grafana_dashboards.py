"""
The Grafana dashboards in ops/grafana/ read only series the services
expose (docs/operations/observability.md), pick histogram buckets that
exist, and import into any Grafana: every panel asks the dashboard's
Prometheus variable and fits the 24-column grid.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.contracts.operator_contract import OperatorContract
from app.gateways.metrics.job_queue_collector import JobQueueCollector
from app.schemas.dto.telemetry import JobQueueMeasurement, JobQueueQuery
from app.utilities.observability.metrics.metrics_exposition import (
    build_metrics_registry,
)
from app.utilities.observability.metrics.prometheus_service_metrics import (
    ANSWER_BUCKETS,
    HTTP_BUCKETS,
    LLM_BUCKETS,
    PICKUP_BUCKETS,
    POOL_WAIT_BUCKETS,
    PrometheusServiceMetrics,
)

type JsonObject = dict[str, Any]

ROOT: Path = Path(__file__).resolve().parents[2]
DASHBOARDS: tuple[Path, ...] = tuple(sorted((ROOT / "ops" / "grafana").glob("*.json")))
DATASOURCE_UID: str = "${datasource}"
GRID_COLUMNS: int = 24
SAMPLE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "counter": ("_total", "_created"),
    "histogram": ("_bucket", "_count", "_sum", "_created"),
    "gauge": ("",),
}
HISTOGRAM_BUCKETS: dict[str, tuple[float, ...]] = {
    "workshop_http_request_duration_seconds": HTTP_BUCKETS,
    "workshop_job_pickup_delay_seconds": PICKUP_BUCKETS,
    "workshop_answer_latency_seconds": ANSWER_BUCKETS,
    "workshop_llm_call_duration_seconds": LLM_BUCKETS,
    "workshop_db_pool_wait_seconds": POOL_WAIT_BUCKETS,
}
SERIES_NAME: re.Pattern[str] = re.compile(r"\b(?:workshop|process)_[a-z_]+\b")
BUCKET_FILTER: re.Pattern[str] = re.compile(r'\b(\w+)_bucket\{le="([^"]+)"\}')


class EmptyQueue(OperatorContract[JobQueueQuery, JobQueueMeasurement]):
    def operate(self, input_data: JobQueueQuery) -> JobQueueMeasurement:
        return JobQueueMeasurement()


def exposed_sample_names() -> set[str]:
    """Every sample name one scrape of an API process can carry."""

    registry = build_metrics_registry(None)
    PrometheusServiceMetrics(registry)
    registry.register(JobQueueCollector(EmptyQueue()))
    names: set[str] = set()
    for family in registry.collect():
        names.update(
            family.name + suffix for suffix in SAMPLE_SUFFIXES.get(family.type, ("",))
        )
        names.update(sample.name for sample in family.samples)

    return names


def load(path: Path) -> JsonObject:
    dashboard: JsonObject = json.loads(path.read_text(encoding="utf-8"))
    return dashboard


def panels_of(dashboard: JsonObject) -> Iterator[JsonObject]:
    for panel in dashboard["panels"]:
        yield panel
        yield from panel.get("panels", [])


def expressions_of(dashboard: JsonObject) -> Iterator[str]:
    for panel in panels_of(dashboard):
        for target in panel.get("targets", []):
            yield str(target["expr"])


def test_there_is_a_dashboard() -> None:
    assert [path.name for path in DASHBOARDS] == ["workshop-service.json"]


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda path: path.name)
def test_every_query_reads_series_the_services_expose(path: Path) -> None:
    exposed = exposed_sample_names()

    unknown = {
        name
        for expression in expressions_of(load(path))
        for name in SERIES_NAME.findall(expression)
        if name not in exposed
    }

    assert unknown == set()


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda path: path.name)
def test_bucket_filters_name_existing_bucket_bounds(path: Path) -> None:
    filters = [
        match.groups()
        for expression in expressions_of(load(path))
        for match in BUCKET_FILTER.finditer(expression)
    ]

    assert filters != []
    for histogram, bound in filters:
        # prometheus_client writes `le` as Python's repr of the bound (60.0).
        assert bound in {repr(edge) for edge in HISTOGRAM_BUCKETS[histogram]}


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda path: path.name)
def test_panels_ask_the_dashboard_datasource_and_fit_the_grid(path: Path) -> None:
    dashboard = load(path)
    panels = list(panels_of(dashboard))
    variables = {item["name"]: item for item in dashboard["templating"]["list"]}

    assert variables["datasource"]["type"] == "datasource"
    assert variables["datasource"]["query"] == "prometheus"
    assert len({panel["id"] for panel in panels}) == len(panels)
    for panel in panels:
        grid = panel["gridPos"]
        assert grid["x"] + grid["w"] <= GRID_COLUMNS, panel["title"]
        if panel["type"] == "row":
            continue
        assert panel["description"], panel["title"]
        assert panel["targets"], panel["title"]
        sources = [panel["datasource"]] + [t["datasource"] for t in panel["targets"]]
        assert {source["uid"] for source in sources} == {DATASOURCE_UID}
