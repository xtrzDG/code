from app.contracts.observability import JobMonitorFacilitatorContract
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.dto.observability import JobCheckIn
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName


class NullJobMonitorFacilitator(JobMonitorFacilitatorContract):
    """Without SENTRY_DSN periodic jobs are only logged, not monitored."""

    def job_started(
        self,
        job_name: JobName,
        interval_seconds: JobIntervalSeconds,
    ) -> JobCheckIn:
        return JobCheckIn(job_name=job_name, interval_seconds=interval_seconds)

    def job_finished(self, check_in: JobCheckIn, outcome: PeriodicJobOutcome) -> None:
        del check_in, outcome
