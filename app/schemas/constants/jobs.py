from enum import StrEnum


class QueuedJobStatus(StrEnum):
    """
    State of a job in the background queue.

    PENDING waits for its `run_at`; RUNNING is claimed by a worker under a
    lease; DONE succeeded; DEAD ran out of attempts (a platform admin may
    retry it); DISCARDED was dropped by a platform admin.
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    DEAD = "dead"
    DISCARDED = "discarded"


class JobLane(StrEnum):
    """
    Worker lane of a queued job. Each lane has its own threads in every
    worker (WORKER_LANE_CONCURRENCY), so a long autotest run never holds up
    a customer message or a notification.
    """

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    DEFAULT = "default"
    AUTOTESTS = "autotests"


class PeriodicJobRunStatus(StrEnum):
    """State of one run of a periodic job in one period."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
