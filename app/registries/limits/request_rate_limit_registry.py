import threading
from collections import deque

from typed_time_provider import Microseconds

from app.contracts.registries import RequestRateLimitRegistryContract

MICROSECONDS_PER_SECOND: int = 1_000_000
# Keys without a recent request are dropped every this many calls.
SWEEP_EVERY_CALLS: int = 1_000


class RequestRateLimitRegistry(RequestRateLimitRegistryContract):
    """
    Sliding-window request counters per key, kept in this process.

    Guards public endpoints (the website widget's polling) against scripts
    that would make the API read a business's data over and over. A
    multi-process deployment counts per process, which still bounds each
    process.
    """

    def __init__(self) -> None:
        self._requests: dict[str, deque[int]] = {}
        self._lock: threading.Lock = threading.Lock()
        self._calls: int = 0

    def try_acquire(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        now: Microseconds,
    ) -> bool:
        window_start: int = int(now) - window_seconds * MICROSECONDS_PER_SECOND
        with self._lock:
            self._calls += 1
            if self._calls % SWEEP_EVERY_CALLS == 0:
                self._sweep(window_start)

            moments: deque[int] = self._requests.setdefault(key, deque())
            while moments and moments[0] <= window_start:
                moments.popleft()

            if len(moments) >= limit:
                return False

            moments.append(int(now))
            return True

    def _sweep(self, window_start: int) -> None:
        for key in [
            key
            for key, moments in self._requests.items()
            if not moments or moments[-1] <= window_start
        ]:
            del self._requests[key]
