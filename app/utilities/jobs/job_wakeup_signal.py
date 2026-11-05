import threading
from collections.abc import Generator
from contextlib import contextmanager

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobWakeupContract
from app.schemas.constants.jobs import JobLane
from app.utilities.jobs.job_wakeup_timer import JobWakeupTimer

MICROSECONDS_PER_SECOND: float = 1_000_000.0


class JobWakeupSignal(JobWakeupContract):
    """
    One event per lane, shared by the job queue facilitator and the lane
    threads of the worker in the same process (the embedded worker in
    development, or a worker that queues follow-up jobs). A woken thread
    claims from the database as usual, so a lost or spurious wake-up only
    costs one poll interval or one empty claim.

    A job queued for later wakes its lane when it is due (`notify_at`):
    while a worker of this process listens, a timer thread
    (`JobWakeupTimer`) sleeps until the earliest such moment; with nobody
    listening there is no lane thread to wake, and nothing is kept.

    Without a database every process is its own world, so there is nothing
    to listen to; on Postgres `PostgresJobWakeupAdapter` carries the signal
    between processes and sets these events.
    """

    def __init__(self, wall_clock: WallClock[Microseconds] | None = None) -> None:
        self._events: dict[JobLane, threading.Event] = {
            lane: threading.Event() for lane in JobLane
        }
        self._wall_clock: WallClock[Microseconds] = (
            WallClock(preferred_time_unit_type=Microseconds)
            if wall_clock is None
            else wall_clock
        )
        self._timer: JobWakeupTimer = JobWakeupTimer(self.notify)
        self._listeners: int = 0
        self._listeners_lock: threading.Lock = threading.Lock()

    def notify(self, lane: JobLane) -> None:
        self._events[lane].set()

    def notify_at(self, lane: JobLane, run_at: Microseconds) -> None:
        with self._listeners_lock:
            if self._listeners == 0:
                return

        delay_seconds: float = (
            int(run_at) - int(self._wall_clock.now_unix())
        ) / MICROSECONDS_PER_SECOND
        self._timer.schedule(lane, int(run_at), delay_seconds)

    def notify_all(self) -> None:
        """Wake every lane (after missed signals, or to notice a stop)."""

        for lane in JobLane:
            self._events[lane].set()

    def wait(self, lane: JobLane, timeout_seconds: float) -> bool:
        event: threading.Event = self._events[lane]
        is_notified: bool = event.wait(timeout=timeout_seconds)
        # Cleared before the caller claims: a job queued after this point
        # sets the event again, so the next wait returns at once.
        event.clear()
        return is_notified

    def has_listeners(self) -> bool:
        """A worker of this process listens (its later jobs get timers)."""

        with self._listeners_lock:
            return self._listeners > 0

    def pending_wakeup_count(self) -> int:
        """Later jobs whose lanes are still to be woken (observability)."""

        return self._timer.pending_count()

    @contextmanager
    def listen(self) -> Generator[None]:
        """Keep the timer of later jobs running while a worker listens."""

        with self._listeners_lock:
            self._listeners += 1
            if self._listeners == 1:
                self._timer.start()
        try:
            yield
        finally:
            with self._listeners_lock:
                self._listeners -= 1
                if self._listeners == 0:
                    self._timer.stop()
