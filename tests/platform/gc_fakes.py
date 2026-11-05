"""A garbage collector that records what it was asked, and a hand-moved clock."""

import threading
from collections.abc import Callable
from typing import Any

from app.contracts.garbage_collection import GarbageCollectorContract, GcCallback
from app.schemas.configurations.garbage_collection_settings import GcThresholds
from app.schemas.typings.observability.constrained_integers import FrozenObjectCount
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)

PYTHON_THRESHOLDS: GcThresholds = GcThresholds(
    young=GcYoungCollectionThreshold(2000),
    middle=GcMiddleCollectionThreshold(10),
    full=GcFullCollectionThreshold(10),
)
STARTUP_HEAP_OBJECTS: int = 1_060_000


class FakeGarbageCollector(GarbageCollectorContract):
    """
    Collects and freezes nothing: it appends each request to `events` (a
    list the test may share with other fakes, to see the order) and, when
    asked to freeze, records what `on_freeze` saw at that moment.
    """

    def __init__(
        self,
        events: list[str] | None = None,
        on_freeze: Callable[[], object] | None = None,
    ) -> None:
        self.events: list[str] = [] if events is None else events
        self.callbacks: list[GcCallback] = []
        self.current_thresholds: GcThresholds = PYTHON_THRESHOLDS
        self.seen_at_freeze: list[object] = []
        self._on_freeze: Callable[[], object] | None = on_freeze
        self._frozen: int = 0
        self._lock: threading.Lock = threading.Lock()

    def collect(self) -> None:
        self._record("collect")

    def freeze(self) -> None:
        self._record("freeze")
        if self._on_freeze is not None:
            self.seen_at_freeze.append(self._on_freeze())
        self._frozen = STARTUP_HEAP_OBJECTS

    def unfreeze(self) -> None:
        self._record("unfreeze")
        self._frozen = 0

    def frozen_object_count(self) -> FrozenObjectCount:
        return FrozenObjectCount(self._frozen)

    def thresholds(self) -> GcThresholds:
        return self.current_thresholds

    def set_thresholds(self, thresholds: GcThresholds) -> None:
        self._record("set_thresholds")
        self.current_thresholds = thresholds

    def add_callback(self, callback: GcCallback) -> None:
        self._record("add_callback")
        self.callbacks.append(callback)

    def remove_callback(self, callback: GcCallback) -> None:
        self._record("remove_callback")
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def run_collection(
        self, generation: int, clock: SteppedClock, seconds: float
    ) -> None:
        """What CPython does around one collection: the callbacks, timed."""

        info: dict[str, Any] = {"generation": generation}
        for callback in list(self.callbacks):
            callback("start", info)
        clock.advance(seconds)
        for callback in list(self.callbacks):
            callback("stop", {**info, "collected": 0, "uncollectable": 0})

    def _record(self, event: str) -> None:
        with self._lock:
            self.events.append(event)


class SteppedClock:
    """Monotonic seconds that move only when the test says so."""

    def __init__(self) -> None:
        self.now: float = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds
