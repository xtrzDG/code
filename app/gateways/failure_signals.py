"""
The failure signals a process counts for the platform health alerts
(LOG-04): refused webhook deliveries, API requests slower than 2 s, and
requests and jobs the database or the object storage failed.

Counting never slows or fails the work it describes: a count is handed to
one background thread (the shared counters are rows of the database), and
each signal counts at most PER_MINUTE_LIMIT times a minute per process, so
a flood of refusals costs a bounded number of writes (the alerts' thresholds
lie far below what the limit lets through).

The HTTP application holds its instance in `app.state.failure_signals`
(`failure_signals_of`); a test application without one counts nothing.
"""

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.contracts.monitoring import SignalCounterAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.utilities.observability.failure_kinds import (
    StoreFailureKind,
    store_failure_of,
)

PER_MINUTE_LIMIT: int = 60
SLOW_REQUEST_SECONDS: float = 2.0
STATE_ATTRIBUTE: str = "failure_signals"
THREAD_NAME_PREFIX: str = "failure-signals"
STORE_SIGNALS: dict[StoreFailureKind, PlatformSignal] = {
    StoreFailureKind.DATABASE: PlatformSignal.DATABASE_ERROR,
    StoreFailureKind.OBJECT_STORAGE: PlatformSignal.OBJECT_STORAGE_ERROR,
}

type Work = Callable[[], None]
type RunLater = Callable[[Work], object]


class FailureSignals:
    """A process's counts of failure signals, written in the background."""

    def __init__(
        self,
        signal_counter: SignalCounterAdapterContract,
        run_later: RunLater | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._counter: SignalCounterAdapterContract = signal_counter
        self._run_later: RunLater | None = run_later
        self._monotonic: Callable[[], float] = monotonic
        self._lock: threading.Lock = threading.Lock()
        self._minutes: dict[PlatformSignal, tuple[int, int]] = {}
        self._executor: ThreadPoolExecutor | None = None

    def count(self, signal: PlatformSignal) -> None:
        """One event of `signal` (dropped past this minute's limit)."""

        if not self._admit(signal):
            return

        self._schedule(lambda: self._counter.count(signal))

    def count_store_failure(self, error: BaseException) -> None:
        """One failure of a store, when `error` comes from one."""

        kind: StoreFailureKind | None = store_failure_of(error)
        if kind is not None:
            self.count(STORE_SIGNALS[kind])

    def count_if_slow(self, elapsed_seconds: float) -> None:
        """One slow API request, when it took 2 s or longer."""

        if elapsed_seconds >= SLOW_REQUEST_SECONDS:
            self.count(PlatformSignal.SLOW_API_REQUEST)

    def close(self) -> None:
        """Write what is scheduled and stop the thread (shutdown)."""

        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

    def _admit(self, signal: PlatformSignal) -> bool:
        minute: int = int(self._monotonic() // 60)
        with self._lock:
            counted_minute, counted = self._minutes.get(signal, (minute, 0))
            if counted_minute != minute:
                counted = 0
            if counted >= PER_MINUTE_LIMIT:
                return False

            self._minutes[signal] = (minute, counted + 1)
            return True

    def _schedule(self, work: Work) -> None:
        if self._run_later is not None:
            self._run_later(work)
            return

        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix=THREAD_NAME_PREFIX
                )
            executor: ThreadPoolExecutor = self._executor
        executor.submit(work)


def failure_signals_of(application: object) -> FailureSignals | None:
    """The failure signals an HTTP application holds (None without)."""

    state: object = getattr(application, "state", None)
    signals: object = getattr(state, STATE_ATTRIBUTE, None)
    return signals if isinstance(signals, FailureSignals) else None
