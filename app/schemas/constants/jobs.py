from enum import StrEnum


class QueuedJobStatus(StrEnum):
    """State of a job in the background queue."""

    PENDING = "pending"
    DONE = "done"
    DEAD = "dead"
