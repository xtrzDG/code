from enum import StrEnum


class KeyRotationStatus(StrEnum):
    """
    State of a re-encryption of the stored secrets with the current key:
    QUEUED until a worker takes the job, RUNNING while it walks every
    business, then DONE (its counts tell whether an old key is still
    needed) or FAILED (the job's last error; a platform admin may start a
    new run).
    """

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
