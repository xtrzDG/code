"""The daily purge keeps the job queue and the periodic runs small."""

from typed_time_provider import Microseconds

from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import PeriodicRunStart
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.jobs.purge_finished_jobs_use_case import PurgeFinishedJobsUseCase
from app.utilities.jobs.periodic_runs import decide_periodic_run_start
from tests.platform.worker_fakes import build_job_stores

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
DAY: int = 86_400_000_000


def test_finished_jobs_and_runs_older_than_30_days_are_purged() -> None:
    stores = build_job_stores()
    ages: dict[QueuedJobStatus, int] = {
        QueuedJobStatus.DONE: 31,
        QueuedJobStatus.DEAD: 45,
        QueuedJobStatus.DISCARDED: 30 + 1,
        QueuedJobStatus.PENDING: 60,
    }
    jobs: dict[QueuedJobStatus, QueuedJobDocument] = {}
    for status, days in ages.items():
        moment = Microseconds(int(NOW) - days * DAY)
        jobs[status] = QueuedJobDocument(
            name=JobName("run_autotests"),
            payload=JobPayloadJson("{}"),
            run_at=moment,
            status=status,
            created_at=moment,
            updated_at=moment,
        )
        stores.job_repo.save(jobs[status])
    recent_dead = QueuedJobDocument(
        name=JobName("run_autotests"),
        payload=JobPayloadJson("{}"),
        run_at=NOW,
        status=QueuedJobStatus.DEAD,
        created_at=NOW,
        updated_at=NOW,
    )
    stores.job_repo.save(recent_dead)
    for period, moment in (
        (JobPeriodKey("2026-08-01"), Microseconds(int(NOW) - 51 * DAY)),
        (JobPeriodKey("2026-09-21"), NOW),
    ):
        stores.periodic_run_repo.claim(
            JobName("send_daily_digest"),
            period,
            decide_periodic_run_start(
                PeriodicRunStart(
                    job_name=JobName("send_daily_digest"),
                    period_key=period,
                    now=moment,
                    lease_until=moment,
                    lease_token=JobLeaseToken("f" * 32),
                )
            ),
        )

    report = PurgeFinishedJobsUseCase(stores.job_repo, stores.periodic_run_repo).run(
        JobTick(job_name=JobName("purge_finished_jobs"), scheduled_at=NOW)
    )

    assert report.processed_count == 4  # three jobs and one periodic run
    remaining = {status for status, job in jobs.items() if stores.job_repo.get(job.id)}
    assert remaining == {QueuedJobStatus.PENDING}
    assert stores.job_repo.get(recent_dead.id) is not None  # still retryable
    assert (
        stores.periodic_run_repo.get(
            JobName("send_daily_digest"), JobPeriodKey("2026-08-01")
        )
        is None
    )
