from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.jobs import PeriodicJobOperator
from app.schemas.typings.platform.booleans import IsProcessLocalJob
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName, JobPeriodKey
from app.utilities.jobs.periodic_runs import compute_period_key


@dataclass(frozen=True)
class PeriodicJobSpec:
    """
    A periodic job: name, interval and the operator that runs it.

    A job runs once per period (`period_key`) across every worker and
    restart, recorded in `periodic_job_runs`. A process-local job (the flush
    of this process's own trace buffer) runs in every worker process on its
    own interval instead and is not recorded.
    """

    name: JobName
    interval_seconds: JobIntervalSeconds
    operator: PeriodicJobOperator
    is_process_local: IsProcessLocalJob = False

    def period_key(self, now: Microseconds) -> JobPeriodKey:
        """The date of a daily job, the ISO week of a weekly one, else the interval."""

        return compute_period_key(self.interval_seconds, now)
