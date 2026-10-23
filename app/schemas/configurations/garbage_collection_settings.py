from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.platform.booleans import IsHeapFreezeAfterWarmupEnabled
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)


class GcThresholds(ImmutableDTO):
    """
    The three thresholds of CPython's cyclic garbage collector, youngest
    generation first (`gc.set_threshold`).
    """

    young: GcYoungCollectionThreshold
    middle: GcMiddleCollectionThreshold
    full: GcFullCollectionThreshold


class GarbageCollectionSettings(ImmutableDTO):
    """
    How the API and worker processes keep garbage collection pauses out of
    the request path (docs/operations/capacity.md, "Garbage collection").

    GC_FREEZE_AFTER_WARMUP (default true): once a process has built its
    container and served its startup steps, it collects once and freezes
    every object alive then (`gc.collect()`, `gc.freeze()`), so later full
    collections no longer walk the startup heap (about a million objects).
    GC_THRESHOLDS ("young,middle,full", e.g. "2000,10,10"; empty: Python's
    own) sets the collector's thresholds for the process's lifetime.
    """

    is_freeze_after_warmup_enabled: IsHeapFreezeAfterWarmupEnabled = True
    thresholds: GcThresholds | None = None
