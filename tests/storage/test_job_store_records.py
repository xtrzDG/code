"""
Listing and purging queued jobs, and periodic run records, on Postgres and
in memory.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import PeriodicJobRunStatus, QueuedJobStatus
from app.schemas.domain.jobs import PeriodicJobRunDocument, QueuedJobDocument
from app.schemas.dto.job_queue import (
    PeriodicRunLease,
    PeriodicRunStart,
    QueuedJobPageQuery,
    QueuedJobPosition,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.jobs.periodic_runs import decide_periodic_run_start
from tests.platform.worker_fakes import JobStores
from tests.storage.job_stores import job_stores_for

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
DAY: int = 86_400_000_000
DIGEST: JobName = JobName("send_daily_digest")
TODAY: JobPeriodKey = JobPeriodKey("2026-09-21")
TOKEN: JobLeaseToken = JobLeaseToken("c" * 32)


@pytest.fixture(params=["in_memory", "postgres"])
def stores(request: pytest.FixtureRequest) -> JobStores:
    return job_stores_for(request)


def add_job(
    stores: JobStores,
    name: str,
    status: QueuedJobStatus,
    updated_days_ago: int,
) -> QueuedJobDocument:
    updated_at = Microseconds(int(NOW) - updated_days_ago * DAY)
    job = QueuedJobDocument(
        name=JobName(name),
        payload=JobPayloadJson("{}"),
        run_at=updated_at,
        status=status,
        created_at=updated_at,
        updated_at=updated_at,
    )
    stores.job_repo.save(job)
    return job


def test_jobs_are_listed_newest_change_first_with_filters(stores: JobStores) -> None:
    dead_old = add_job(stores, "run_autotests", QueuedJobStatus.DEAD, 3)
    done = add_job(stores, "run_autotests", QueuedJobStatus.DONE, 2)
    dead_new = add_job(stores, "end_trials", QueuedJobStatus.DEAD, 1)
    pending = add_job(stores, "run_autotests", QueuedJobStatus.PENDING, 0)

    everything = stores.job_repo.list_page(QueuedJobPageQuery(page_size=PageSize(10)))
    dead = stores.job_repo.list_page(
        QueuedJobPageQuery(status=QueuedJobStatus.DEAD, page_size=PageSize(10))
    )
    dead_autotests = stores.job_repo.list_page(
        QueuedJobPageQuery(
            status=QueuedJobStatus.DEAD,
            name=JobName("run_autotests"),
            page_size=PageSize(10),
        )
    )
    first_page = stores.job_repo.list_page(QueuedJobPageQuery(page_size=PageSize(1)))
    second_page = stores.job_repo.list_page(
        QueuedJobPageQuery(
            after=QueuedJobPosition(
                updated_at=first_page[0].updated_at, job_id=first_page[0].id
            ),
            page_size=PageSize(1),
        )
    )

    assert [job.id for job in everything] == [
        pending.id,
        dead_new.id,
        done.id,
        dead_old.id,
    ]
    assert [job.id for job in dead] == [dead_new.id, dead_old.id]
    assert [job.id for job in dead_autotests] == [dead_old.id]
    # One more than the page size, so the caller knows a page follows.
    assert [job.id for job in first_page] == [pending.id, dead_new.id]
    assert [job.id for job in second_page] == [dead_new.id, done.id]


def test_only_old_finished_jobs_are_purged(stores: JobStores) -> None:
    kept = [
        add_job(stores, "run_autotests", QueuedJobStatus.PENDING, 90),
        add_job(stores, "run_autotests", QueuedJobStatus.RUNNING, 90),
        add_job(stores, "run_autotests", QueuedJobStatus.DONE, 29),
        add_job(stores, "run_autotests", QueuedJobStatus.DEAD, 10),
    ]
    purged = [
        add_job(stores, "run_autotests", status, 31)
        for status in (
            QueuedJobStatus.DONE,
            QueuedJobStatus.DEAD,
            QueuedJobStatus.DISCARDED,
        )
    ]

    count = stores.job_repo.purge_finished(Microseconds(int(NOW) - 30 * DAY))

    assert count == 3
    assert all(stores.job_repo.get(job.id) is not None for job in kept)
    assert all(stores.job_repo.get(job.id) is None for job in purged)


def start(now: Microseconds) -> PeriodicRunStart:
    return PeriodicRunStart(
        job_name=DIGEST,
        period_key=TODAY,
        now=now,
        lease_until=Microseconds(int(now) + 120_000_000),
        lease_token=TOKEN,
    )


def test_a_period_starts_once_and_is_finished_by_its_holder(stores: JobStores) -> None:
    runs = stores.periodic_run_repo

    started = runs.claim(DIGEST, TODAY, decide_periodic_run_start(start(NOW)))
    again = runs.claim(DIGEST, TODAY, decide_periodic_run_start(start(NOW)))
    assert started is not None and again is None
    assert started.status is PeriodicJobRunStatus.RUNNING

    later = Microseconds(int(NOW) + 60_000_000)
    lease = PeriodicRunLease(
        job_name=DIGEST,
        period_key=TODAY,
        lease_token=TOKEN,
        lease_until=Microseconds(int(later) + 120_000_000),
    )
    assert runs.extend_lease(lease)
    assert not runs.extend_lease(
        lease.model_copy(update={"lease_token": JobLeaseToken("d" * 32)})
    )
    finished: PeriodicJobRunDocument = started.model_copy(deep=True)
    finished.status = PeriodicJobRunStatus.SUCCEEDED
    finished.finished_at = later
    finished.lease_token = None
    assert runs.finish(finished, TOKEN)
    assert not runs.finish(finished, TOKEN)  # no longer running
    assert runs.get(DIGEST, TODAY) == finished
    assert runs.claim(DIGEST, TODAY, decide_periodic_run_start(start(later))) is None


def test_old_periodic_runs_are_purged(stores: JobStores) -> None:
    runs = stores.periodic_run_repo
    old_day = Microseconds(int(NOW) - 31 * DAY)
    old_period = JobPeriodKey("2026-08-21")
    runs.claim(
        DIGEST,
        old_period,
        decide_periodic_run_start(
            start(old_day).model_copy(update={"period_key": old_period})
        ),
    )
    runs.claim(DIGEST, TODAY, decide_periodic_run_start(start(NOW)))

    count = runs.purge_started_before(Microseconds(int(NOW) - 30 * DAY))

    assert count == 1
    assert runs.get(DIGEST, old_period) is None
    assert runs.get(DIGEST, TODAY) is not None
