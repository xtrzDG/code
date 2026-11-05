"""
Wake-ups at a moment: a job queued for later (a burst of customer messages
answered once the customer is quiet, a retry after its backoff) wakes its
lane when it becomes due instead of at the lane's next poll.

One thread per listening worker sleeps until the earliest pending wake-up
(a heap ordered by deadline), wakes that job's lane and sleeps again. A due
time arrives as wall-clock microseconds (the queue's `run_at`) and is turned
into a monotonic deadline once, when it is scheduled, so a frozen or
adjusted wall clock never makes the thread spin.
"""

import heapq
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.schemas.constants.jobs import JobLane

LOGGER: logging.Logger = logging.getLogger(__name__)
TIMER_THREAD_NAME: str = "job-wakeup-timer"
# A lane is woken this long after its job's due time, so the worker's own
# clock has passed `run_at` when the woken thread claims (the monotonic and
# the wall clock may drift apart by a little).
WAKE_MARGIN_SECONDS: float = 0.005
# Pending wake-ups at most; one more is dropped, and the lane's poll finds
# its job (the safety net of every wake-up).
MAX_PENDING_WAKEUPS: int = 10_000
STOP_SECONDS: float = 2.0


@dataclass(order=True, frozen=True)
class PendingWakeup:
    """One scheduled wake-up: when (monotonic seconds) and which lane."""

    deadline: float
    lane: JobLane = field(compare=False)
    # The job's due time (wall-clock microseconds): one wake-up per lane
    # and due time, however often it was announced.
    due_microseconds: int = field(compare=False)


class JobWakeupTimer:
    """
    The pending wake-ups of one process and the thread that fires them
    (`start` .. `stop`, the worker's listening). `take_due` is the step the
    thread repeats; tests call it with their own monotonic clock.
    """

    def __init__(
        self,
        wake: Callable[[JobLane], None],
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._wake: Callable[[JobLane], None] = wake
        self._monotonic: Callable[[], float] = monotonic
        # Re-entrant: the thread reads `take_due` while holding it.
        self._condition: threading.Condition = threading.Condition(threading.RLock())
        self._pending: list[PendingWakeup] = []
        self._scheduled: set[tuple[JobLane, int]] = set()
        self._thread: threading.Thread | None = None
        self._is_stopping: bool = False

    def schedule(
        self, lane: JobLane, due_microseconds: int, delay_seconds: float
    ) -> bool:
        """
        Wake `lane` in `delay_seconds` (its job is due at `due_microseconds`);
        False when the wake-up is left to the polls (too many pending).
        """

        key: tuple[JobLane, int] = (lane, due_microseconds)
        with self._condition:
            if key in self._scheduled:
                return True

            if len(self._pending) >= MAX_PENDING_WAKEUPS:
                LOGGER.warning("Too many pending job wake-ups; the polls take over")
                return False

            deadline: float = (
                self._monotonic() + max(0.0, delay_seconds) + WAKE_MARGIN_SECONDS
            )
            heapq.heappush(
                self._pending, PendingWakeup(deadline, lane, due_microseconds)
            )
            self._scheduled.add(key)
            self._condition.notify_all()

        return True

    def take_due(self) -> tuple[list[JobLane], float | None]:
        """
        Remove the wake-ups whose deadline passed and return their lanes
        (each once), with the seconds until the next one (None: none left).
        """

        with self._condition:
            now: float = self._monotonic()
            lanes: list[JobLane] = []
            while self._pending and self._pending[0].deadline <= now:
                due: PendingWakeup = heapq.heappop(self._pending)
                self._scheduled.discard((due.lane, due.due_microseconds))
                if due.lane not in lanes:
                    lanes.append(due.lane)

            if not self._pending:
                return lanes, None

            return lanes, self._pending[0].deadline - now

    def pending_count(self) -> int:
        with self._condition:
            return len(self._pending)

    def start(self) -> None:
        """Fire wake-ups from a daemon thread until `stop`."""

        with self._condition:
            if self._thread is not None:
                return

            self._is_stopping = False
            self._thread = threading.Thread(
                target=self._run, name=TIMER_THREAD_NAME, daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        """End the thread; pending wake-ups are dropped (nobody listens)."""

        with self._condition:
            thread: threading.Thread | None = self._thread
            self._is_stopping = True
            self._pending.clear()
            self._scheduled.clear()
            self._condition.notify_all()

        if thread is not None:
            thread.join(timeout=STOP_SECONDS)

        with self._condition:
            self._thread = None

    def _run(self) -> None:
        while (lanes := self._wait_for_due()) is not None:
            for lane in lanes:
                self._wake(lane)

    def _wait_for_due(self) -> list[JobLane] | None:
        """
        The next due lanes, waiting for them; None once stopping. Reading
        the deadline and waiting are one step under the condition, so a
        sooner wake-up scheduled meanwhile is never slept through.
        """

        with self._condition:
            while not self._is_stopping:
                lanes, wait_seconds = self.take_due()
                if lanes:
                    return lanes

                self._condition.wait(timeout=wait_seconds)

        return None
