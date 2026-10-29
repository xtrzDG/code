"""
The garbage collector's series (docs/operations/observability.md), on the
registry of one application container: how long its collections stopped
the process, by generation, and how much of its heap is frozen.
"""

from prometheus_client import CollectorRegistry, Gauge, Histogram

from app.schemas.constants.observability import GcGeneration
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.schemas.typings.observability.constrained_integers import FrozenObjectCount

# A young collection takes well under a millisecond; a full one of an
# unfrozen startup heap a second or more (docs/operations/capacity.md).
GC_PAUSE_BUCKETS: tuple[float, ...] = (
    0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0,
    2.5, 5.0,
)  # fmt: skip


class PrometheusGcMetrics:
    """
    One process's garbage collection series. The pause histogram has a
    series per generation from the start (a generation that never ran shows
    zero), so a scrape always finds all three.
    """

    def __init__(self, registry: CollectorRegistry) -> None:
        pauses = Histogram(
            "workshop_gc_pause_seconds",
            "Garbage collections of the process by generation: every thread "
            "waits while one runs.",
            ["generation"],
            buckets=GC_PAUSE_BUCKETS,
            registry=registry,
        )
        self._pauses: dict[GcGeneration, Histogram] = {
            generation: pauses.labels(generation=generation.value)
            for generation in GcGeneration
        }
        self._frozen_objects = Gauge(
            "workshop_gc_frozen_objects",
            "Objects of the startup heap the collector no longer scans "
            "(GC_FREEZE_AFTER_WARMUP); 0 until the process has warmed up.",
            registry=registry,
            # Across the processes of an instance: the least frozen one, so
            # a process that runs without a frozen heap shows as 0.
            multiprocess_mode="livemin",
        )

    def observe_pause(self, generation: GcGeneration, pause: ObservedSeconds) -> None:
        self._pauses[generation].observe(float(pause))

    def set_frozen_objects(self, count: FrozenObjectCount) -> None:
        self._frozen_objects.set(int(count))
