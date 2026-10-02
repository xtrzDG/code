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

    Guards public endpoints (the website widget's polling and messages)
    against scripts that would make the API read a business's data or call
    the model over and over. A
    multi-process deployment counts per process, which still bounds each
    process.
    """

    def __init__(self) -> None:
        self._requests: dict[str, deque[int]] = {}
        self._lock: threading.Lock = threading.Lock()
        self._calls: int = 0

    def try_acquire_all(
        self,
        counters: list[tuple[str, int]],
        window_seconds: int,
        now: Microseconds,
    ) -> str | None:
        window_start: int = int(now) - window_seconds * MICROSECONDS_PER_SECOND
        with self._lock:
            self._calls += 1
            if self._calls % SWEEP_EVERY_CALLS == 0:
                self._sweep(window_start)

            for key, limit in counters:
                moments: deque[int] | None = self._requests.get(key)
                if moments is None:
                    continue

                while moments and moments[0] <= window_start:
                    moments.popleft()
                if len(moments) >= limit:
                    return key

            for key, _ in counters:
                self._requests.setdefault(key, deque()).append(int(now))

            return None

    def seconds_until_free(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        now: Microseconds,
    ) -> int:
        window: int = window_seconds * MICROSECONDS_PER_SECOND
        window_start: int = int(now) - window
        with self._lock:
            moments: list[int] = [
                moment
                for moment in self._requests.get(key, deque())
                if moment > window_start
            ]

        if len(moments) < limit:
            return 0

        # The request that frees a place is the one `limit` places from the
        # newest; it leaves the window `window` after it was made.
        freeing_moment: int = moments[len(moments) - limit]
        wait: int = freeing_moment + window - int(now)
        return max(1, -(-wait // MICROSECONDS_PER_SECOND))

    def _sweep(self, window_start: int) -> None:
        for key in [
            key
            for key, moments in self._requests.items()
            if not moments or moments[-1] <= window_start
        ]:
            del self._requests[key]
