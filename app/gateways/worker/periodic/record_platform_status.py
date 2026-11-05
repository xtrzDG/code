"""
The status page's history (`RecordPlatformStatusUseCase`) as a periodic
job of the background worker: every five minutes one worker folds every
component's level now (the platform alerts that fire, the announcements
in effect) into today's row, so the ninety-day bars show the worst of
each day even after an episode is over.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

RECORD_PLATFORM_STATUS_JOB: JobName = JobName("record_platform_status")
RECORD_PLATFORM_STATUS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(5 * 60)


def record_platform_status_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every five minutes."""

    return PeriodicJobSpec(
        name=RECORD_PLATFORM_STATUS_JOB,
        interval_seconds=RECORD_PLATFORM_STATUS_INTERVAL,
        operator=operator,
    )
