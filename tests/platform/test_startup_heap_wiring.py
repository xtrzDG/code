"""
The API and the worker freeze their startup heap once: after their
container is built and their startup steps ran, before the first request
or job, and give it back when they stop. The GC series are on the
process's metrics registry.
"""

import gc
import os
import signal
import threading
from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from app.containers.app import AppContainer
from app.gateways.worker.background_worker import BackgroundWorker
from app.main import create_application
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.observability.garbage_collection.gc_pause_recorder import (
    GcPauseRecorder,
)
from app.worker_main import STOP_SIGNALS, main
from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.workshop_container import replace_provider
from tests.platform.gc_fakes import FakeGarbageCollector

FREEZING_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "GC_FREEZE_AFTER_WARMUP": "true",
    "GC_THRESHOLDS": "5000,20,30",
}
METRICS_TOKEN: str = "test-token-0000"  # gitleaks:allow
GENERATIONS: frozenset[str] = frozenset({"0", "1", "2"})
SETTLED: list[str] = ["set_thresholds", "collect", "freeze", "add_callback"]
RELEASED: list[str] = ["remove_callback", "unfreeze", "set_thresholds"]


def requests_answered(workshop: Workshop) -> float:
    registry = workshop.container.utilities.metrics_registry()
    return sum(
        sample.value
        for family in registry.collect()
        if family.name == "workshop_http_request_duration_seconds"
        for sample in family.samples
        if sample.name.endswith("_count")
    )


def test_the_api_freezes_after_its_startup_steps_and_before_any_request() -> None:
    started: dict[str, Workshop] = {}
    collector = FakeGarbageCollector(
        on_freeze=lambda: (
            # The last startup step pointed the platform bot at the API.
            "setWebhook" in "".join(started["workshop"].telegram.paths()),
            requests_answered(started["workshop"]),
        )
    )
    workshop = start_workshop(
        FREEZING_ENVIRONMENT,
        lambda container: replace_provider(
            container.utilities.garbage_collector, collector
        ),
    )
    started["workshop"] = workshop
    # Built, routers and operators included, but not started: nothing yet.
    assert collector.events == []

    with workshop.client:
        at_startup: list[str] = list(collector.events)
        assert workshop.client.get("/healthz").status_code == 200
        assert workshop.client.get("/healthz").status_code == 200

    assert at_startup == SETTLED
    assert collector.seen_at_freeze == [(True, 0.0)]
    assert collector.events == SETTLED + RELEASED
    assert collector.callbacks == []


@pytest.fixture
def restored_signal_handlers() -> Iterator[None]:
    previous = {
        stop_signal: signal.getsignal(stop_signal) for stop_signal in STOP_SIGNALS
    }
    yield
    for stop_signal, handler in previous.items():
        signal.signal(stop_signal, handler)


class RecordingWorker:
    """Stands in for the background worker: notes when it starts serving."""

    def __init__(self, events: list[str]) -> None:
        self._events: list[str] = events

    def run_forever(self, stop_event: threading.Event) -> None:
        assert stop_event.is_set()
        self._events.append("run_forever")


@pytest.mark.usefixtures("restored_signal_handlers")
def test_the_worker_freezes_after_its_startup_and_before_its_first_job() -> None:
    events: list[str] = []
    collector = FakeGarbageCollector(events)
    workshop = start_workshop(FREEZING_ENVIRONMENT)
    container: AppContainer = workshop.container
    replace_provider(container.utilities.garbage_collector, collector)
    replace_provider(
        container.gateways.background_worker,
        cast(BackgroundWorker, RecordingWorker(events)),
    )
    stop_event = threading.Event()
    stop_event.set()

    assert main(app_container=container, stop_event=stop_event) == 0

    assert events == [*SETTLED, "run_forever", *RELEASED]


@pytest.fixture
def metered_empty_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for variable in list(os.environ):
        monkeypatch.delenv(variable)
    monkeypatch.setenv("METRICS_TOKEN", METRICS_TOKEN)

    yield


def gc_samples(page: str) -> dict[str, dict[str, float]]:
    """GC samples of a metrics page: by sample name, then by generation."""

    samples: dict[str, dict[str, float]] = {}
    for family in text_string_to_metric_families(page):
        for sample in family.samples:
            if sample.name.startswith("workshop_gc_"):
                generation: str = sample.labels.get("generation", "")
                samples.setdefault(sample.name, {})[generation] = sample.value

    return samples


def pause_callbacks() -> list[object]:
    return [
        callback
        for callback in gc.callbacks
        if isinstance(getattr(callback, "__self__", None), GcPauseRecorder)
    ]


@pytest.mark.usefixtures("metered_empty_environment")
def test_a_real_api_process_keeps_its_heap_frozen_only_while_it_serves() -> None:
    frozen_before: int = gc.get_freeze_count()
    application = create_application()
    # The container and the routers exist; the heap is not frozen yet.
    assert gc.get_freeze_count() == frozen_before

    with TestClient(application) as client:
        frozen: int = gc.get_freeze_count()
        callbacks = pause_callbacks()
        page = client.get(
            "/metrics", headers={"Authorization": f"Bearer {METRICS_TOKEN}"}
        )

    assert page.status_code == 200
    # An API process's startup heap: hundreds of thousands of objects.
    assert frozen - frozen_before > 200_000
    samples = gc_samples(page.text)
    # The gauge counted at the freeze; frozen objects freed since (work in
    # flight then) leave the count.
    assert samples["workshop_gc_frozen_objects"][""] >= frozen
    assert set(samples["workshop_gc_pause_seconds_count"]) == GENERATIONS
    assert len(callbacks) == 1
    assert gc.get_freeze_count() == frozen_before
    assert pause_callbacks() == []


def test_the_gc_series_are_on_the_process_registry() -> None:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings({}))

    container.utilities.startup_heap_tuner()
    families = {
        family.name: family
        for family in container.utilities.metrics_registry().collect()
    }

    pauses = families["workshop_gc_pause_seconds"]
    assert pauses.type == "histogram"
    assert {sample.labels.get("generation") for sample in pauses.samples} == GENERATIONS
    assert families["workshop_gc_frozen_objects"].type == "gauge"
