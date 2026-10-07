"""
Poison jobs: a job whose attempts keep ending with their worker process
(killed, out of memory) is set aside after the second such attempt in a
row, as DEAD with the reason process_died and an error report, instead of
taking down worker after worker. A recorded result in between starts the
count again.
"""

from app.gateways.worker.queued_job_runner import (
    JobKilledItsWorkerError,
    QueuedJobRunner,
)
from app.schemas.constants.jobs import JobDeathReason, JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobClaimLimit,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.job_runner_fakes import build_runner
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    FlakyQueuedOperator,
    JobStores,
    RecordingErrorReporter,
    build_job_stores,
    build_worker,
)

PAST_THE_LEASE_SECONDS: int = 121


def enqueue(clock: ControlledClock, stores: JobStores) -> QueuedJobId:
    kit = build_worker(clock, [], stores=stores)
    return kit.queue.enqueue(RUN_AUTOTESTS, JobPayloadJson("{}"), None)


def stored(stores: JobStores, job_id: QueuedJobId) -> QueuedJobDocument:
    job = stores.job_repo.get(job_id)
    assert job is not None
    return job


def claim_and_die(runner: QueuedJobRunner, clock: ControlledClock) -> None:
    """A worker claims the job and its process ends; the reaper notices."""

    claimed, _ = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    assert len(claimed) == 1
    clock.advance(PAST_THE_LEASE_SECONDS)
    runner.release_expired_leases()


def test_the_second_attempt_in_a_row_that_kills_its_worker_is_the_last() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    errors = RecordingErrorReporter()
    runner, _, _ = build_runner(clock, stores, operator, errors)
    job_id = enqueue(clock, stores)

    claim_and_die(runner, clock)
    after_first = stored(stores, job_id)
    claim_and_die(runner, clock)
    dead = stored(stores, job_id)
    claimed_again, _ = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))

    assert after_first.status is QueuedJobStatus.PENDING
    assert int(after_first.lost_leases) == 1
    assert after_first.dead_reason is None
    assert dead.status is QueuedJobStatus.DEAD
    assert dead.dead_reason is JobDeathReason.PROCESS_DIED
    assert int(dead.lost_leases) == 2
    assert int(dead.attempts) == 2
    assert str(dead.last_error).startswith("process_died:")
    assert claimed_again == []
    assert operator.calls == []
    # Reported (Sentry) once, and the dead_jobs alert counts the DEAD job.
    [report] = errors.errors
    assert isinstance(report, JobKilledItsWorkerError)
    assert str(job_id) in str(report)


def test_a_recorded_result_starts_the_count_again() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    # The second attempt fails as a job (a recorded result), the next one
    # succeeds.
    operator = FlakyQueuedOperator(failures_before_success=1)
    runner, _, _ = build_runner(clock, stores, operator)
    job_id = enqueue(clock, stores)

    claim_and_die(runner, clock)
    claimed, token = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    runner.run(claimed[0], token)
    after_retry = stored(stores, job_id)
    clock.advance(10 * 60)
    claim_and_die(runner, clock)
    after_second_death = stored(stores, job_id)

    assert after_retry.status is QueuedJobStatus.PENDING
    assert int(after_retry.lost_leases) == 0
    assert after_second_death.status is QueuedJobStatus.PENDING
    assert int(after_second_death.lost_leases) == 1

    clock.advance(10 * 60)
    claimed, token = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    runner.run(claimed[0], token)
    done = stored(stores, job_id)

    assert done.status is QueuedJobStatus.DONE
    assert int(done.lost_leases) == 0
    assert done.dead_reason is None


def test_a_lost_last_attempt_dies_of_its_attempts() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    runner, _, _ = build_runner(clock, stores, FlakyQueuedOperator(0))
    job_id = enqueue(clock, stores)
    job = stored(stores, job_id)
    job.attempts = JobAttemptCount(4)
    stores.job_repo.save(job)

    claim_and_die(runner, clock)
    dead = stored(stores, job_id)

    assert dead.status is QueuedJobStatus.DEAD
    assert dead.dead_reason is JobDeathReason.ATTEMPTS_EXHAUSTED
    assert "Lease expired" in str(dead.last_error)


def test_jobs_that_fail_or_have_no_handler_say_why_they_died() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    always_failing = FlakyQueuedOperator(failures_before_success=10)
    kit = build_worker(clock, [], {RUN_AUTOTESTS: always_failing}, stores=stores)
    failing = kit.queue.enqueue(RUN_AUTOTESTS, JobPayloadJson("{}"), None)
    unknown = kit.queue.enqueue(
        JobName("job_nobody_handles"), JobPayloadJson("{}"), None
    )

    for _ in range(5):
        kit.worker.run_queued_jobs()
        clock.advance(60 * 60)

    assert stored(stores, failing).dead_reason is JobDeathReason.ATTEMPTS_EXHAUSTED
    assert stored(stores, unknown).dead_reason is JobDeathReason.NO_HANDLER
