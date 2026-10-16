"""
The daily purge of stale rows as a periodic job of the background worker:
expired sessions, login codes older than a day, and webhook receipts older
than 30 days (`PurgeStaleRowsUseCase`). Registered with one line in the
worker's list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_STALE_ROWS_JOB: JobName = JobName("purge_stale_rows")
PURGE_STALE_ROWS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def purge_stale_rows_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=PURGE_STALE_ROWS_JOB,
        interval_seconds=PURGE_STALE_ROWS_INTERVAL,
        operator=operator,
    )
