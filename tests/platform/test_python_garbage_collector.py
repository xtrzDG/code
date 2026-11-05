"""
The `gc` module behind GarbageCollectorContract: thresholds read and set,
callbacks added once and removed, the heap frozen and given back.
"""

import gc
from collections.abc import Iterator
from typing import Any

import pytest

from app.schemas.configurations.garbage_collection_settings import GcThresholds
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)
from app.utilities.observability.garbage_collection.python_garbage_collector import (
    PythonGarbageCollector,
)

TUNED: GcThresholds = GcThresholds(
    young=GcYoungCollectionThreshold(7000),
    middle=GcMiddleCollectionThreshold(15),
    full=GcFullCollectionThreshold(25),
)


@pytest.fixture
def restored_collector() -> Iterator[None]:
    """Whatever a test changes in this process's collector is put back."""

    thresholds = gc.get_threshold()
    callbacks = list(gc.callbacks)
    was_frozen: bool = gc.get_freeze_count() > 0
    was_enabled: bool = gc.isenabled()
    yield
    gc.set_threshold(*thresholds)
    gc.callbacks[:] = callbacks
    if was_frozen:
        gc.freeze()
    else:
        gc.unfreeze()
    if was_enabled:
        gc.enable()


@pytest.mark.usefixtures("restored_collector")
def test_the_thresholds_are_python_s_and_set_for_the_process() -> None:
    collector = PythonGarbageCollector()
    young, middle, full = gc.get_threshold()
    assert collector.thresholds() == GcThresholds(
        young=GcYoungCollectionThreshold(young),
        middle=GcMiddleCollectionThreshold(middle),
        full=GcFullCollectionThreshold(full),
    )

    collector.set_thresholds(TUNED)

    assert gc.get_threshold() == (7000, 15, 25)
    assert collector.thresholds() == TUNED


@pytest.mark.usefixtures("restored_collector")
def test_a_callback_is_called_around_every_collection_and_added_once() -> None:
    # Only the collections asked for here: none starts by itself meanwhile.
    gc.disable()
    collector = PythonGarbageCollector()
    phases: list[tuple[str, int]] = []

    def record(phase: str, info: dict[str, Any]) -> None:
        phases.append((phase, info["generation"]))

    collector.add_callback(record)
    collector.add_callback(record)
    collector.collect()
    collector.remove_callback(record)
    collector.remove_callback(record)
    collector.collect()

    assert phases == [("start", 2), ("stop", 2)]
    assert record not in gc.callbacks


@pytest.mark.usefixtures("restored_collector")
def test_freezing_moves_the_heap_out_of_the_generations_until_unfrozen() -> None:
    collector = PythonGarbageCollector()
    frozen_before: int = gc.get_freeze_count()

    collector.freeze()
    frozen = collector.frozen_object_count()
    collector.unfreeze()

    # The test process's own heap: pytest, the application's modules.
    assert int(frozen) > frozen_before + 10_000
    assert int(collector.frozen_object_count()) == 0
    assert gc.get_freeze_count() == 0
