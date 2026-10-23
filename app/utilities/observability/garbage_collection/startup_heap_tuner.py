"""
Garbage collection pauses out of the request path: one process's collector
over its lifetime (docs/operations/capacity.md, "Garbage collection").

A full collection walks every object the process tracks; an API process
tracks about a million after startup (the container's providers, the
pydantic and FastAPI schemas), and under load such a walk stopped every
thread for one to five seconds. Those objects live as long as the process,
so once it has warmed up (its container built, its startup steps done,
before it serves) they are collected once and frozen: later collections
skip them.
"""

import logging
import threading
import time
from collections.abc import Callable

from app.contracts.garbage_collection import GarbageCollectorContract
from app.schemas.configurations.garbage_collection_settings import (
    GarbageCollectionSettings,
    GcThresholds,
)
from app.schemas.typings.observability.constrained_integers import FrozenObjectCount
from app.utilities.observability.garbage_collection.gc_pause_recorder import (
    GcPauseRecorder,
)
from app.utilities.observability.metrics.prometheus_gc_metrics import (
    PrometheusGcMetrics,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
MILLISECONDS_PER_SECOND: float = 1000.0


class StartupHeapTuner:
    """
    `settle_after_warmup` once the process's container is built and warmed,
    just before it serves (GC_THRESHOLDS, the freeze, then the pause
    metrics); `release` when it stops: the frozen objects go back to the
    collector and its thresholds are restored, so a process that starts the
    application again (tests do) starts clean. Thread-safe; each step
    happens at most once.
    """

    def __init__(
        self,
        collector: GarbageCollectorContract,
        settings: GarbageCollectionSettings,
        metrics: PrometheusGcMetrics,
        monotonic: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._collector: GarbageCollectorContract = collector
        self._settings: GarbageCollectionSettings = settings
        self._metrics: PrometheusGcMetrics = metrics
        self._monotonic: Callable[[], float] = monotonic
        self._recorder: GcPauseRecorder = GcPauseRecorder(
            collector, metrics, monotonic=monotonic
        )
        self._lock: threading.Lock = threading.Lock()
        self._previous_thresholds: GcThresholds | None = None
        self._has_settled: bool = False
        self._is_recording: bool = False
        self._is_frozen: bool = False

    def settle_after_warmup(self) -> None:
        """
        Once, after warm-up: set GC_THRESHOLDS, collect and freeze what is
        left (unless GC_FREEZE_AFTER_WARMUP is false), then time every
        collection.
        """

        with self._lock:
            if self._has_settled:
                return

            self._has_settled = True
            self._apply_thresholds()
            if self._settings.is_freeze_after_warmup_enabled:
                self._freeze_startup_heap()
            else:
                LOGGER.info(
                    "GC_FREEZE_AFTER_WARMUP is off: full collections walk the "
                    "startup heap too"
                )

            self._recorder.start()
            self._is_recording = True

    def release(self) -> None:
        """Stop timing collections, unfreeze, restore the thresholds."""

        with self._lock:
            if self._is_recording:
                self._recorder.stop()
                self._is_recording = False

            if self._is_frozen:
                self._collector.unfreeze()
                self._metrics.set_frozen_objects(FrozenObjectCount(0))
                self._is_frozen = False

            if self._previous_thresholds is not None:
                self._collector.set_thresholds(self._previous_thresholds)
                self._previous_thresholds = None

    def _apply_thresholds(self) -> None:
        thresholds: GcThresholds | None = self._settings.thresholds
        if thresholds is None:
            return

        self._previous_thresholds = self._collector.thresholds()
        self._collector.set_thresholds(thresholds)
        LOGGER.info(
            "Garbage collector thresholds (GC_THRESHOLDS): %d, %d, %d",
            int(thresholds.young),
            int(thresholds.middle),
            int(thresholds.full),
        )

    def _freeze_startup_heap(self) -> None:
        started: float = self._monotonic()
        self._collector.collect()
        self._collector.freeze()
        self._is_frozen = True
        frozen: FrozenObjectCount = self._collector.frozen_object_count()
        self._metrics.set_frozen_objects(frozen)
        LOGGER.info(
            "Startup heap frozen after warm-up: %d objects leave the garbage "
            "collector's generations (collected and frozen in %.0f ms)",
            int(frozen),
            (self._monotonic() - started) * MILLISECONDS_PER_SECOND,
        )
