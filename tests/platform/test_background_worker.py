"""The background worker runs periodic jobs on time and retries queued jobs."""

from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.worker_fakes import (
    ControlledClock,
    CountingPeriodicOperator,
    FlakyQueuedOperator,
    build_worker,
)


def test_periodic_jobs_respect_their_interval_and_isolate_failures() -> None:
    clock = ControlledClock()
    hourly = CountingPeriodicOperator()
    broken = CountingPeriodicOperator(should_fail=True)
    worker, _, _, reporter = build_worker(
        clock,
        [
            PeriodicJobSpec(
                name=JobName("purge_expired_recordings"),
                interval_seconds=JobIntervalSeconds(3600),
                operator=hourly,
            ),
            PeriodicJobSpec(
                name=JobName("broken_job"),
                interval_seconds=JobIntervalSeconds(60),
                operator=broken,
            ),
        ],
        None,
    )

    first = worker.run_once()
    clock.advance(120)
    second = worker.run_once()
    clock.advance(3600)
    worker.run_once()

    assert first.periodic_runs == 2 and first.failures == 1
    assert second.periodic_runs == 1
    assert len(hourly.ticks) == 2
    assert len(broken.ticks) == 3
    assert len(reporter.errors) == 3


def test_queued_job_is_retried_with_backoff_then_done() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=2)
    worker, job_repo, queue, reporter = build_worker(clock, [], operator)
    job_id = queue.enqueue(
        JobName("run_autotests"),
        JobPayloadJson('{"assistant_version_id": "v1"}'),
        business_id=None,
    )

    worker.run_once()
    failed_once = job_repo.get(job_id)
    assert failed_once is not None
    assert failed_once.status is QueuedJobStatus.PENDING
    assert failed_once.attempts == 1
    assert failed_once.last_error == "ExternalServiceError: provider down"

    clock.advance(10)
    worker.run_once()
    assert len(operator.calls) == 1

    clock.advance(30)
    worker.run_once()
    clock.advance(60)
    worker.run_once()

    done = job_repo.get(job_id)
    assert done is not None
    assert done.status is QueuedJobStatus.DONE
    assert len(operator.calls) == 3
    assert reporter.errors == []


def test_queued_job_dies_after_max_attempts_or_without_handler() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=100)
    worker, job_repo, queue, reporter = build_worker(clock, [], operator)
    job_id = queue.enqueue(
        JobName("run_autotests"),
        JobPayloadJson("{}"),
        business_id=None,
    )
    orphan_id = queue.enqueue(
        JobName("unknown_job"),
        JobPayloadJson("{}"),
        business_id=None,
    )

    for _ in range(10):
        worker.run_once()
        clock.advance(10_000)

    dead = job_repo.get(job_id)
    orphan = job_repo.get(orphan_id)
    assert dead is not None and dead.status is QueuedJobStatus.DEAD
    assert dead.attempts == 5
    # Only the last attempt is marked final, so a handler can clean up then.
    assert [call.is_final_attempt for call in operator.calls] == [False] * 4 + [True]
    assert orphan is not None and orphan.status is QueuedJobStatus.DEAD
    assert reporter.errors == []
