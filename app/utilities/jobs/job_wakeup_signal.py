import threading
from collections.abc import Generator
from contextlib import contextmanager

from app.contracts.jobs import JobWakeupContract
from app.schemas.constants.jobs import JobLane


class JobWakeupSignal(JobWakeupContract):
    """
    One event per lane, shared by the job queue facilitator and the lane
    threads of the worker in the same process (the embedded worker in
    development, or a worker that queues follow-up jobs). A woken thread
    claims from the database as usual, so a lost or spurious wake-up only
    costs one poll interval or one empty claim.

    Without a database every process is its own world, so there is nothing
    to listen to; on Postgres `PostgresJobWakeupAdapter` carries the signal
    between processes and sets these events.
    """

    def __init__(self) -> None:
        self._events: dict[JobLane, threading.Event] = {
            lane: threading.Event() for lane in JobLane
        }

    def notify(self, lane: JobLane) -> None:
        self._events[lane].set()

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

    @contextmanager
    def listen(self) -> Generator[None]:
        yield
