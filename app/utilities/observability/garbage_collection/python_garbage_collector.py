"""CPython's cyclic garbage collector of this process (the `gc` module)."""

import gc

from app.contracts.garbage_collection import GarbageCollectorContract, GcCallback
from app.schemas.configurations.garbage_collection_settings import GcThresholds
from app.schemas.typings.observability.constrained_integers import FrozenObjectCount
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)


class PythonGarbageCollector(GarbageCollectorContract):
    """The `gc` module itself: one collector per process, shared by its threads."""

    def collect(self) -> None:
        gc.collect()

    def freeze(self) -> None:
        gc.freeze()

    def unfreeze(self) -> None:
        gc.unfreeze()

    def frozen_object_count(self) -> FrozenObjectCount:
        return FrozenObjectCount(gc.get_freeze_count())

    def thresholds(self) -> GcThresholds:
        young, middle, full = gc.get_threshold()
        return GcThresholds(
            young=GcYoungCollectionThreshold(young),
            middle=GcMiddleCollectionThreshold(middle),
            full=GcFullCollectionThreshold(full),
        )

    def set_thresholds(self, thresholds: GcThresholds) -> None:
        gc.set_threshold(
            int(thresholds.young), int(thresholds.middle), int(thresholds.full)
        )

    def add_callback(self, callback: GcCallback) -> None:
        if callback not in gc.callbacks:
            gc.callbacks.append(callback)

    def remove_callback(self, callback: GcCallback) -> None:
        if callback in gc.callbacks:
            gc.callbacks.remove(callback)
