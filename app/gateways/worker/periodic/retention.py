"""
The nightly retention purge as a periodic job of the background worker:
each business's customer data past the periods it chose in Settings →
Privacy (`PurgeExpiredPersonalDataUseCase`). Registered with one line in
the worker's list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_EXPIRED_PERSONAL_DATA_JOB: JobName = JobName("purge_expired_personal_data")
PURGE_EXPIRED_PERSONAL_DATA_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(
    24 * 60 * 60
)


def retention_purge_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` once a day."""

    return PeriodicJobSpec(
        name=PURGE_EXPIRED_PERSONAL_DATA_JOB,
        interval_seconds=PURGE_EXPIRED_PERSONAL_DATA_INTERVAL,
        operator=operator,
    )
