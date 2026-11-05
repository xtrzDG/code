"""
The process's cyclic garbage collector (CPython's `gc` module), behind a
contract: startup heap tuning is tested with a fake, without collecting or
freezing the test process.
"""

from collections.abc import Callable
from typing import Any, Protocol

from app.contracts.utility_contract import UtilityContract
from app.schemas.configurations.garbage_collection_settings import GcThresholds
from app.schemas.typings.observability.constrained_integers import FrozenObjectCount

# What `gc.callbacks` calls before and after each collection: the phase
# ("start" or "stop") and the collection's facts ("generation", ...).
type GcCallback = Callable[[str, dict[str, Any]], None]


class GarbageCollectorContract(UtilityContract, Protocol):
    def collect(self) -> None:
        """Collect every generation now (a full collection)."""
        raise NotImplementedError

    def freeze(self) -> None:
        """Move every tracked object out of the generations; never scanned again."""
        raise NotImplementedError

    def unfreeze(self) -> None:
        """Give the frozen objects back to the oldest generation."""
        raise NotImplementedError

    def frozen_object_count(self) -> FrozenObjectCount:
        raise NotImplementedError

    def thresholds(self) -> GcThresholds:
        """The thresholds in force now."""
        raise NotImplementedError

    def set_thresholds(self, thresholds: GcThresholds) -> None:
        raise NotImplementedError

    def add_callback(self, callback: GcCallback) -> None:
        """Call `callback` before and after every collection of the process."""
        raise NotImplementedError

    def remove_callback(self, callback: GcCallback) -> None:
        """Stop calling `callback` (nothing happens when it was not added)."""
        raise NotImplementedError
