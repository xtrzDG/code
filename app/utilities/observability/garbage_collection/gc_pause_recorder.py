"""
Times every garbage collection of the process and hands the pauses to the
metrics outside the collection.

A collection can start inside any allocation, also while a thread holds a
metric's lock (prometheus_client creates values under its lock), so the
collector's callback never touches a lock: it appends the pause to a queue
of its generation, and a thread of its own observes the queued pauses every
few seconds (and once more when recording stops).
"""

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from app.contracts.garbage_collection import GarbageCollectorContract
from app.schemas.constants.observability import GcGeneration
from app.utilities.observability.metrics.observed_durations import observed_seconds
from app.utilities.observability.metrics.prometheus_gc_metrics import (
    PrometheusGcMetrics,
)

GC_PAUSE_FLUSH_SECONDS: float = 5.0
GC_PAUSE_FLUSH_THREAD_NAME: str = "gc-pause-metrics"
# Pauses waiting for the next flush, per generation; beyond this (a flush
# thread starved for minutes) the oldest are dropped, memory stays bounded.
MAX_PENDING_PAUSES: int = 100_000
GC_START_PHASE: str = "start"
# `gc.callbacks` names the generation by its number.
GENERATIONS_BY_NUMBER: dict[int, GcGeneration] = {
    int(generation.value): generation for generation in GcGeneration
}


class GcPauseRecorder:
    """
    One process's collections, from `start` to `stop`. Collections never
    overlap (CPython runs one at a time, its callbacks included), so the
    start of the running one is a single moment.
    """

    def __init__(
        self,
        collector: GarbageCollectorContract,
        metrics: PrometheusGcMetrics,
        flush_seconds: float = GC_PAUSE_FLUSH_SECONDS,
        monotonic: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._collector: GarbageCollectorContract = collector
        self._metrics: PrometheusGcMetrics = metrics
        self._flush_seconds: float = flush_seconds
        self._monotonic: Callable[[], float] = monotonic
        self._collection_started: float = 0.0
        self._pending: dict[GcGeneration, deque[float]] = {
            generation: deque(maxlen=MAX_PENDING_PAUSES) for generation in GcGeneration
        }
        self._stop_event: threading.Event = threading.Event()
        self._flush_thread: threading.Thread | None = None

    def start(self) -> None:
        """Time the collections from now on (once; later calls do nothing)."""

        if self._flush_thread is not None:
            return

        self._flush_thread = threading.Thread(
            target=self._flush_until_stopped,
            name=GC_PAUSE_FLUSH_THREAD_NAME,
            daemon=True,
        )
        self._collector.add_callback(self.on_collection)
        self._flush_thread.start()

    def stop(self) -> None:
        """Stop timing; every pause timed so far reaches the metrics."""

        self._collector.remove_callback(self.on_collection)
        self._stop_event.set()
        if self._flush_thread is not None:
            self._flush_thread.join()

        self.flush()

    def on_collection(self, phase: str, info: dict[str, Any]) -> None:
        """The collector's callback: before ("start") and after each collection."""

        if phase == GC_START_PHASE:
            self._collection_started = self._monotonic()
            return

        generation: GcGeneration | None = GENERATIONS_BY_NUMBER.get(
            info.get("generation", -1)
        )
        if generation is not None:
            self._pending[generation].append(
                self._monotonic() - self._collection_started
            )

    def flush(self) -> None:
        """Observe the queued pauses (any thread; never inside a collection)."""

        for generation, pending in self._pending.items():
            while pending:
                try:
                    pause: float = pending.popleft()
                except IndexError:  # another flush took the last one
                    break

                self._metrics.observe_pause(generation, observed_seconds(pause))

    def _flush_until_stopped(self) -> None:
        while not self._stop_event.wait(timeout=self._flush_seconds):
            self.flush()
