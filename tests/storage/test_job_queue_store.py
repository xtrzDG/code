"""The leased job queue behaves the same on Postgres and in memory."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobDeathReason, JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import (
    ExpiredLeaseRelease,
    HeldJobLease,
    JobClaimRequest,
    JobLeaseExtension,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobClaimLimit,
    LostJobLeaseCount,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobSerialKey,
)
from app.schemas.typings.platform.strings import JobErrorText, JobPayloadJson
from tests.platform.worker_fakes import JobStores
from tests.storage.job_stores import job_stores_for

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
SECOND: int = 1_000_000
FIRST_TOKEN: JobLeaseToken = JobLeaseToken("a" * 32)
SECOND_TOKEN: JobLeaseToken = JobLeaseToken("b" * 32)


@pytest.fixture(params=["in_memory", "postgres"])
def stores(request: pytest.FixtureRequest) -> JobStores:
    return job_stores_for(request)


def add_job(
    stores: JobStores,
    run_at_seconds: int = 0,
    lane: JobLane = JobLane.DEFAULT,
    serial_key: str | None = None,
    status: QueuedJobStatus = QueuedJobStatus.PENDING,
    business_id: BusinessId | None = None,
) -> QueuedJobDocument:
    run_at = Microseconds(int(NOW) + run_at_seconds * SECOND)
    job = QueuedJobDocument(
        name=JobName("send_booking_reminders"),
        payload=JobPayloadJson('{"text": "შეხსენება"}'),
        business_id=business_id,
        lane=lane,
        serial_key=None if serial_key is None else JobSerialKey(serial_key),
        run_at=run_at,
        status=status,
        created_at=run_at,
        updated_at=run_at,
    )
    stores.job_repo.save(job)
    return job


def claim(
    stores: JobStores,
    lane: JobLane = JobLane.DEFAULT,
    limit: int = 10,
    token: JobLeaseToken = FIRST_TOKEN,
    at_seconds: int = 0,
) -> list[QueuedJobDocument]:
    now = Microseconds(int(NOW) + at_seconds * SECOND)
    return stores.job_repo.claim_due(
        JobClaimRequest(
            lane=lane,
            now=now,
            limit=JobClaimLimit(limit),
            lease_until=Microseconds(int(now) + 120 * SECOND),
            lease_token=token,
        )
    )


def test_due_jobs_of_the_lane_are_leased_oldest_first(stores: JobStores) -> None:
    later = add_job(stores, run_at_seconds=-10)
    oldest = add_job(stores, run_at_seconds=-30, business_id=BusinessId())
    add_job(stores, run_at_seconds=60)  # not due yet
    add_job(stores, run_at_seconds=-60, lane=JobLane.AUTOTESTS)
    add_job(stores, run_at_seconds=-90, status=QueuedJobStatus.DONE)

    claimed = claim(stores)

    assert [job.id for job in claimed] == [oldest.id, later.id]
    for job in claimed:
        assert job.status is QueuedJobStatus.RUNNING
        assert job.attempts == JobAttemptCount(1)
        assert job.lease_until == Microseconds(int(NOW) + 120 * SECOND)
        assert job.lease_token == FIRST_TOKEN
        assert job.updated_at == NOW
        assert stores.job_repo.get(job.id) == job

    # Claimed jobs are not claimed again; the limit holds.
    assert claim(stores, token=SECOND_TOKEN) == []
    assert [job.lane for job in claim(stores, JobLane.AUTOTESTS, limit=1)] == [
        JobLane.AUTOTESTS
    ]


def test_a_serial_key_runs_one_job_at_a_time(stores: JobStores) -> None:
    first = add_job(stores, -30, JobLane.AUTOTESTS, "autotests:salon")
    second = add_job(stores, -20, JobLane.AUTOTESTS, "autotests:salon")
    other = add_job(stores, -10, JobLane.AUTOTESTS, "autotests:cafe")

    claimed = claim(stores, JobLane.AUTOTESTS)
    blocked = claim(stores, JobLane.AUTOTESTS, token=SECOND_TOKEN)
    first_running = claimed[0]
    first_running.status = QueuedJobStatus.DONE
    assert stores.job_repo.settle(first_running, FIRST_TOKEN)
    after_first = claim(stores, JobLane.AUTOTESTS, token=SECOND_TOKEN)

    assert [job.id for job in claimed] == [first.id, other.id]
    assert blocked == []
    assert [job.id for job in after_first] == [second.id]


def test_only_the_lease_holder_extends_or_settles_a_job(stores: JobStores) -> None:
    job = add_job(stores, -1)
    (running,) = claim(stores)
    extended = stores.job_repo.extend_leases(
        JobLeaseExtension(
            leases=[
                HeldJobLease(job_id=job.id, lease_token=FIRST_TOKEN),
                HeldJobLease(job_id=add_job(stores, 600).id, lease_token=FIRST_TOKEN),
            ],
            lease_until=Microseconds(int(NOW) + 300 * SECOND),
        )
    )
    stolen = stores.job_repo.extend_leases(
        JobLeaseExtension(
            leases=[HeldJobLease(job_id=job.id, lease_token=SECOND_TOKEN)],
            lease_until=Microseconds(int(NOW) + 900 * SECOND),
        )
    )

    assert extended == [job.id]
    assert stolen == []
    stored = stores.job_repo.get(job.id)
    assert stored is not None
    assert stored.lease_until == Microseconds(int(NOW) + 300 * SECOND)
    running.status = QueuedJobStatus.DONE
    assert not stores.job_repo.settle(running, SECOND_TOKEN)
    assert stores.job_repo.settle(running, FIRST_TOKEN)
    assert not stores.job_repo.settle(running, FIRST_TOKEN)  # no longer running


def test_expired_leases_are_released_or_the_job_dies(stores: JobStores) -> None:
    retried = add_job(stores, -5)
    exhausted = add_job(stores, -4)
    exhausted.attempts = JobAttemptCount(4)
    stores.job_repo.save(exhausted)
    # Its previous attempt ended with its worker too.
    poison = add_job(stores, -3)
    poison.lost_leases = LostJobLeaseCount(1)
    stores.job_repo.save(poison)
    claim(stores)
    alive = add_job(stores, 100)
    claim(stores, at_seconds=100, token=SECOND_TOKEN)

    released = stores.job_repo.release_expired_leases(
        ExpiredLeaseRelease(
            now=Microseconds(int(NOW) + 150 * SECOND),
            max_attempts=JobAttemptCount(5),
            error_text=JobErrorText("Lease expired."),
            max_lost_leases=LostJobLeaseCount(2),
            process_died_text=JobErrorText("process_died: set aside."),
        )
    )

    by_id = {job.id: job for job in released}
    assert set(by_id) == {retried.id, exhausted.id, poison.id}
    assert by_id[retried.id].status is QueuedJobStatus.PENDING
    assert by_id[retried.id].run_at == Microseconds(int(NOW) + 150 * SECOND)
    assert by_id[retried.id].dead_reason is None
    assert by_id[exhausted.id].status is QueuedJobStatus.DEAD
    assert by_id[exhausted.id].dead_reason is JobDeathReason.ATTEMPTS_EXHAUSTED
    assert by_id[poison.id].status is QueuedJobStatus.DEAD
    assert by_id[poison.id].dead_reason is JobDeathReason.PROCESS_DIED
    assert by_id[poison.id].last_error == "process_died: set aside."
    for job in released:
        assert job.lease_until is None and job.lease_token is None
        assert int(job.lost_leases) == (2 if job.id == poison.id else 1)
        if job.id != poison.id:
            assert job.last_error == "Lease expired."
        assert stores.job_repo.get(job.id) == job

    still_running = stores.job_repo.get(alive.id)
    assert still_running is not None
    assert still_running.status is QueuedJobStatus.RUNNING


def test_a_stopping_worker_hands_back_only_what_it_still_holds(
    stores: JobStores,
) -> None:
    job = add_job(stores)
    [running] = claim(stores)
    later = Microseconds(int(NOW) + 30 * SECOND)

    stolen = stores.job_repo.hand_back(
        HeldJobLease(job_id=job.id, lease_token=SECOND_TOKEN), later
    )
    handed = stores.job_repo.hand_back(
        HeldJobLease(job_id=job.id, lease_token=FIRST_TOKEN), later
    )
    again = stores.job_repo.hand_back(
        HeldJobLease(job_id=job.id, lease_token=FIRST_TOKEN), later
    )

    assert int(running.attempts) == 1
    assert (stolen, handed, again) == (False, True, False)
    stored = stores.job_repo.get(job.id)
    assert stored is not None
    assert stored.status is QueuedJobStatus.PENDING
    assert int(stored.attempts) == 0
    assert stored.run_at == later
    assert stored.lease_token is None and stored.lease_until is None
