"""
The worker's log lines around one job: when it was picked up (the pickup
delay, the queue-to-claim SLI of docs/operations/capacity.md) and how it
ended, with how long it ran and the process's resident memory before and
after it (`rss_before_mb`, `rss_after_mb`), so a job that bloats or kills
its worker can be found in the logs.
"""

import logging
import time
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.constrained_integers import (
    ElapsedMilliseconds,
    ResidentMemoryBytes,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.log_formatting import log_fields
from app.utilities.observability.process_memory import (
    megabytes,
    resident_memory_bytes,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_MILLISECOND: int = 1_000
MILLISECONDS_PER_SECOND: int = 1_000


@dataclass(frozen=True)
class JobRunStart:
    """When a job started in this process and how much memory it held then."""

    started_at: float
    rss_before: ResidentMemoryBytes | None


def start_job_run() -> JobRunStart:
    """Note the start of a job (monotonic time and the RSS before it)."""

    return JobRunStart(started_at=time.monotonic(), rss_before=resident_memory_bytes())


def log_job_finished(job_name: JobName, outcome: str, start: JobRunStart) -> None:
    """
    One line per finished job: its outcome, how long it ran and the RSS
    before and after it (within the job's log context).
    """

    elapsed = ElapsedMilliseconds(
        max(0, int((time.monotonic() - start.started_at) * MILLISECONDS_PER_SECOND))
    )
    fields: dict[str, int | str] = {"duration_ms": int(elapsed), "outcome": outcome}
    readings: dict[str, int | None] = {
        "rss_before_mb": megabytes(start.rss_before),
        "rss_after_mb": megabytes(resident_memory_bytes()),
    }
    fields.update(
        (name, value) for name, value in readings.items() if value is not None
    )
    LOGGER.info(
        "Job %s %s in %d ms; RSS %s MB before, %s MB after",
        job_name,
        outcome,
        int(elapsed),
        fields.get("rss_before_mb", "?"),
        fields.get("rss_after_mb", "?"),
        extra=log_fields(**fields),
    )


def log_pickup(job: QueuedJobDocument, claimed_at: Microseconds) -> None:
    """
    One line per claimed job with `pickup_delay_ms`: how long it waited
    between being due (queued for now, or its retry time) and a worker
    taking it, the queue-to-claim SLI of docs/operations/capacity.md. A job
    whose last worker died with it says so (`lost_leases`).
    """

    delay = ElapsedMilliseconds(
        max(0, (int(claimed_at) - int(job.run_at)) // MICROSECONDS_PER_MILLISECOND)
    )
    with bound_log_context(
        job_name=job.name, job_id=job.id, business_id=job.business_id
    ):
        LOGGER.info(
            "Picked up job %s on the %s lane %d ms after it was due",
            job.name,
            job.lane.value,
            int(delay),
            extra=log_fields(
                pickup_delay_ms=int(delay),
                lane=job.lane.value,
                attempt=int(job.attempts),
                lost_leases=int(job.lost_leases),
            ),
        )
