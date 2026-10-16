"""
Deleting the archives of full business exports whose download link ran
out, as a periodic job of the background worker: hourly, across every
business (`PurgeBusinessExportsUseCase`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_BUSINESS_EXPORTS_JOB: JobName = JobName("purge_business_exports")
PURGE_BUSINESS_EXPORTS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def purge_business_exports_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=PURGE_BUSINESS_EXPORTS_JOB,
        interval_seconds=PURGE_BUSINESS_EXPORTS_INTERVAL,
        operator=operator,
    )
