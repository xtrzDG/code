"""
The service level indicators (`RecordServiceLevelsUseCase`,
docs/operations/slo.md) as a periodic job of the background worker: every
five minutes one worker judges the customer messages of the slots whose
60 s are over, writes the row of every hour that ended, and removes old
slots and rows. The error budget card and the burn-rate alerts read them.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

RECORD_SLI_JOB: JobName = JobName("record_sli")
RECORD_SLI_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(5 * 60)


def record_service_levels_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every five minutes."""

    return PeriodicJobSpec(
        name=RECORD_SLI_JOB,
        interval_seconds=RECORD_SLI_INTERVAL,
        operator=operator,
    )
