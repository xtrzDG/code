"""
The API availability SLI of one API process (docs/operations/slo.md): every
answered request is counted in memory per five-minute slot, and as a
server error when its status is 5xx; every 15 s a flush thread adds the
counts to the shared slots (`add_api_request_counts`), so the processes of
every instance add up. A failed flush keeps its counts for the next one.
"""

import logging
import threading
from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.jobs import JobReport
from app.schemas.dto.service_levels import ApiRequestCounts, ApiRequestSlotCount
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.utilities.observability.service_levels import slot_start_of

LOGGER: logging.Logger = logging.getLogger(__name__)
FLUSH_INTERVAL_SECONDS: float = 15.0
SERVER_ERROR: int = 500
THREAD_NAME: str = "api-availability-flush"

type AddApiRequestCountsOperator = OperatorContract[ApiRequestCounts, JobReport]


class ApiAvailabilityTally:
    """Thread-safe counts of this process, keyed by slot start."""

    def __init__(
        self,
        operator: AddApiRequestCountsOperator,
        wall_clock: WallClock[Microseconds],
        flush_seconds: float = FLUSH_INTERVAL_SECONDS,
    ) -> None:
        self._operator: AddApiRequestCountsOperator = operator
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._flush_seconds: float = flush_seconds
        self._lock: threading.Lock = threading.Lock()
        self._counts: dict[int, list[int]] = {}
        self._stop: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None

    def count(self, status: int) -> None:
        """One answered request with this HTTP status (cheap, never raises)."""

        slot: int = int(slot_start_of(int(self._wall_clock.now_unix())))
        with self._lock:
            cell: list[int] = self._counts.setdefault(slot, [0, 0])
            cell[0] += 1
            if status >= SERVER_ERROR:
                cell[1] += 1

    def flush(self) -> None:
        """Add what was counted to the shared slots (kept when that fails)."""

        with self._lock:
            taken: dict[int, list[int]] = self._counts
            self._counts = {}
        if not taken:
            return

        try:
            self._operator.operate(counts_of(taken))
        except Exception as error:  # noqa: BLE001 - counting never fails a request
            LOGGER.warning("API request counts not stored yet: %s", error)
            self._put_back(taken)

    def start(self) -> None:
        """Flush every 15 s on a daemon thread (once per process)."""

        if self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._flush_periodically(self._stop.wait),
            name=THREAD_NAME,
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        """Stop the thread and flush what is left (shutdown)."""

        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._flush_seconds)
        self.flush()

    def _flush_periodically(self, wait: Callable[[float], bool]) -> Callable[[], None]:
        def run() -> None:
            while not wait(self._flush_seconds):
                self.flush()

        return run

    def _put_back(self, taken: dict[int, list[int]]) -> None:
        with self._lock:
            for slot, (requests, errors) in taken.items():
                cell: list[int] = self._counts.setdefault(slot, [0, 0])
                cell[0] += requests
                cell[1] += errors


def counts_of(taken: dict[int, list[int]]) -> ApiRequestCounts:
    return ApiRequestCounts(
        slots=[
            ApiRequestSlotCount(
                slot_start=Microseconds(slot),
                requests=ServiceLevelEventCount(requests),
                server_errors=ServiceLevelEventCount(errors),
            )
            for slot, (requests, errors) in sorted(taken.items())
        ]
    )
