from typed_time_provider import Microseconds

from app.contracts.jobs import PeriodicJobRunRepoContract, QueuedJobRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import (
    JobRetentionDays,
    ProcessedItemCount,
)

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
FINISHED_JOB_RETENTION_DAYS: JobRetentionDays = JobRetentionDays(30)


class PurgeFinishedJobsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job: delete queued jobs that finished (done, dead or discarded)
    more than FINISHED_JOB_RETENTION_DAYS ago, and the run records of
    periodic jobs from periods that started before then, so the queue
    tables stop growing. A dead job stays retryable for those 30 days.
    """

    def __init__(
        self,
        job_repo: QueuedJobRepoContract,
        periodic_run_repo: PeriodicJobRunRepoContract,
    ) -> None:
        self._job_repo: QueuedJobRepoContract = job_repo
        self._periodic_run_repo: PeriodicJobRunRepoContract = periodic_run_repo

    def run(self, input_data: JobTick) -> JobReport:
        cutoff = Microseconds(
            int(input_data.scheduled_at)
            - int(FINISHED_JOB_RETENTION_DAYS) * MICROSECONDS_PER_DAY
        )
        purged_jobs: ProcessedItemCount = self._job_repo.purge_finished(cutoff)
        purged_runs: ProcessedItemCount = self._periodic_run_repo.purge_started_before(
            cutoff
        )
        return JobReport(
            processed_count=ProcessedItemCount(int(purged_jobs) + int(purged_runs))
        )
