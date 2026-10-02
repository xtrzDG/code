import threading

from app.contracts.jobs import JobWakeupContract
from app.schemas.constants.jobs import JobLane


class JobWakeupSignal(JobWakeupContract):
    """
    One event per lane, shared by the job queue facilitator and the lane
    threads of the worker in the same process (the embedded worker in
    development, or a worker that queues follow-up jobs). A woken thread
    claims from the database as usual, so a lost or spurious wake-up only
    costs one poll interval or one empty claim.
    """

    def __init__(self) -> None:
        self._events: dict[JobLane, threading.Event] = {
            lane: threading.Event() for lane in JobLane
        }

    def notify(self, lane: JobLane) -> None:
        self._events[lane].set()

    def wait(self, lane: JobLane, timeout_seconds: float) -> bool:
        event: threading.Event = self._events[lane]
        is_notified: bool = event.wait(timeout=timeout_seconds)
        # Cleared before the caller claims: a job queued after this point
        # sets the event again, so the next wait returns at once.
        event.clear()
        return is_notified
