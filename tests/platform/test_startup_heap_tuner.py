"""
The startup heap and the collector's pauses, step by step over a recording
collector: thresholds, one collection and one freeze after warm-up, pauses
timed by generation and observed outside the collection, everything given
back on shutdown.
"""

import threading

import pytest
from prometheus_client import CollectorRegistry

from app.schemas.configurations.garbage_collection_settings import (
    GarbageCollectionSettings,
    GcThresholds,
)
from app.schemas.constants.observability import GcGeneration
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)
from app.utilities.observability.garbage_collection.gc_pause_recorder import (
    GcPauseRecorder,
)
from app.utilities.observability.garbage_collection.startup_heap_tuner import (
    StartupHeapTuner,
)
from app.utilities.observability.metrics.prometheus_gc_metrics import (
    PrometheusGcMetrics,
)
from tests.platform.gc_fakes import (
    PYTHON_THRESHOLDS,
    STARTUP_HEAP_OBJECTS,
    FakeGarbageCollector,
    SteppedClock,
)

TUNED: GcThresholds = GcThresholds(
    young=GcYoungCollectionThreshold(5000),
    middle=GcMiddleCollectionThreshold(20),
    full=GcFullCollectionThreshold(30),
)
SETTLING_THREADS: int = 8


def tuner_over(
    collector: FakeGarbageCollector,
    settings: GarbageCollectionSettings,
    registry: CollectorRegistry,
) -> StartupHeapTuner:
    return StartupHeapTuner(collector, settings, PrometheusGcMetrics(registry))


def frozen_gauge(registry: CollectorRegistry) -> float | None:
    return registry.get_sample_value("workshop_gc_frozen_objects")


def pause_sample(
    registry: CollectorRegistry, suffix: str, generation: str, **labels: str
) -> float | None:
    return registry.get_sample_value(
        f"workshop_gc_pause_seconds_{suffix}", {"generation": generation, **labels}
    )


def test_after_warm_up_the_heap_is_collected_then_frozen_once() -> None:
    collector = FakeGarbageCollector()
    registry = CollectorRegistry()
    tuner = tuner_over(collector, GarbageCollectionSettings(thresholds=TUNED), registry)

    tuner.settle_after_warmup()
    tuner.settle_after_warmup()

    assert collector.events == ["set_thresholds", "collect", "freeze", "add_callback"]
    assert collector.current_thresholds == TUNED
    assert frozen_gauge(registry) == STARTUP_HEAP_OBJECTS
    assert len(collector.callbacks) == 1


def test_without_the_freeze_python_keeps_its_heap_and_thresholds() -> None:
    collector = FakeGarbageCollector()
    registry = CollectorRegistry()
    tuner = tuner_over(
        collector,
        GarbageCollectionSettings(is_freeze_after_warmup_enabled=False),
        registry,
    )

    tuner.settle_after_warmup()

    # Only the pauses are timed.
    assert collector.events == ["add_callback"]
    assert collector.current_thresholds == PYTHON_THRESHOLDS
    assert frozen_gauge(registry) == 0


def test_release_gives_the_heap_and_the_thresholds_back_once() -> None:
    collector = FakeGarbageCollector()
    registry = CollectorRegistry()
    tuner = tuner_over(collector, GarbageCollectionSettings(thresholds=TUNED), registry)
    tuner.release()
    assert collector.events == []

    tuner.settle_after_warmup()
    tuner.release()
    tuner.release()

    assert collector.events[4:] == ["remove_callback", "unfreeze", "set_thresholds"]
    assert collector.current_thresholds == PYTHON_THRESHOLDS
    assert collector.callbacks == []
    assert frozen_gauge(registry) == 0


def test_racing_settles_collect_and_freeze_once() -> None:
    collector = FakeGarbageCollector()
    tuner = tuner_over(collector, GarbageCollectionSettings(), CollectorRegistry())
    barrier = threading.Barrier(SETTLING_THREADS)

    def settle() -> None:
        barrier.wait()
        tuner.settle_after_warmup()

    threads = [threading.Thread(target=settle) for _ in range(SETTLING_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert collector.events == ["collect", "freeze", "add_callback"]
    tuner.release()


def test_pauses_are_timed_by_generation_and_observed_after_the_collection() -> None:
    collector = FakeGarbageCollector()
    clock = SteppedClock()
    registry = CollectorRegistry()
    recorder = GcPauseRecorder(
        collector, PrometheusGcMetrics(registry), monotonic=clock
    )
    recorder.start()

    collector.run_collection(0, clock, 0.0004)
    collector.run_collection(2, clock, 1.5)
    collector.run_collection(1, clock, 0.003)
    # Not a generation of CPython's collector: ignored.
    collector.run_collection(7, clock, 9.0)

    # Nothing is observed inside a collection.
    assert pause_sample(registry, "count", "0") == 0
    recorder.flush()
    assert pause_sample(registry, "count", "0") == 1
    assert pause_sample(registry, "sum", "0") == pytest.approx(0.0004)
    assert pause_sample(registry, "bucket", "2", le="1.0") == 0
    assert pause_sample(registry, "bucket", "2", le="2.5") == 1
    assert pause_sample(registry, "bucket", "1", le="0.005") == 1
    recorder.stop()
    assert collector.callbacks == []


class LockedMetrics(PrometheusGcMetrics):
    """Metrics whose observation needs a lock, as prometheus_client's do."""

    def __init__(self, registry: CollectorRegistry) -> None:
        super().__init__(registry)
        self.lock: threading.Lock = threading.Lock()
        self.observed: threading.Event = threading.Event()

    def observe_pause(self, generation: GcGeneration, pause: ObservedSeconds) -> None:
        if not self.lock.acquire(blocking=False):
            raise AssertionError("a pause was observed while its lock was held")
        try:
            super().observe_pause(generation, pause)
            self.observed.set()
        finally:
            self.lock.release()


def test_a_collection_inside_a_metric_lock_never_waits_for_it() -> None:
    collector = FakeGarbageCollector()
    clock = SteppedClock()
    registry = CollectorRegistry()
    metrics = LockedMetrics(registry)
    recorder = GcPauseRecorder(
        collector, metrics, flush_seconds=3600.0, monotonic=clock
    )
    recorder.start()

    # A collection that starts while this thread holds the metric's lock
    # (an allocation under it) only queues its pause.
    with metrics.lock:
        collector.run_collection(2, clock, 2.0)

    recorder.stop()

    assert pause_sample(registry, "count", "2") == 1
    assert pause_sample(registry, "sum", "2") == 2.0


def test_the_flush_thread_observes_while_recording() -> None:
    collector = FakeGarbageCollector()
    clock = SteppedClock()
    registry = CollectorRegistry()
    metrics = LockedMetrics(registry)
    recorder = GcPauseRecorder(collector, metrics, flush_seconds=0.01, monotonic=clock)
    recorder.start()
    recorder.start()

    collector.run_collection(0, clock, 0.001)

    assert metrics.observed.wait(timeout=10.0)
    assert pause_sample(registry, "count", "0") == 1
    recorder.stop()
    assert collector.events == ["add_callback", "remove_callback"]


def test_every_generation_has_a_series_before_its_first_collection() -> None:
    registry = CollectorRegistry()
    PrometheusGcMetrics(registry)

    assert [
        pause_sample(registry, "count", generation.value) for generation in GcGeneration
    ] == [0, 0, 0]
    assert frozen_gauge(registry) == 0
