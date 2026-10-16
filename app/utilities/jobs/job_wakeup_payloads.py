"""
The payload of a job wake-up NOTIFY: the lane (`inbound`), or the lane and
when its job is due, in wall-clock microseconds (`inbound@1790000000000000`).
A worker of an older release reads the second form as an unknown lane and
ignores it (its polls find the job), so both releases can run side by side.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobLane

DUE_SEPARATOR: str = "@"


def encode_job_wakeup(lane: JobLane, run_at: Microseconds | None = None) -> str:
    if run_at is None:
        return lane.value

    return f"{lane.value}{DUE_SEPARATOR}{int(run_at)}"


def decode_job_wakeup(payload: str) -> tuple[JobLane, Microseconds | None] | None:
    """The lane and the due time of a payload; None for one of another release."""

    lane_value, separator, due = payload.partition(DUE_SEPARATOR)
    try:
        lane = JobLane(lane_value)
    except ValueError:
        return None

    if not separator:
        return lane, None

    if not due.isascii() or not due.isdigit():
        return None

    return lane, Microseconds(int(due))
