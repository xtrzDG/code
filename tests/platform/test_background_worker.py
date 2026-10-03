"""The background worker runs periodic jobs on time and retries queued jobs."""

from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    CountingPeriodicOperator,
    FlakyQueuedOperator,
    build_worker,
)


def test_periodic_jobs_respect_their_period_and_isolate_failures() -> None:
    clock = ControlledClock()
    hourly = CountingPeriodicOperator()
    broken = CountingPeriodicOperator(should_fail=True)
    kit = build_worker(
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
    )

    first = kit.worker.run_once()
    clock.advance(120)
    second = kit.worker.run_once()
    clock.advance(3600)
    kit.worker.run_once()

    assert first.periodic_runs == 2 and first.failures == 1
    assert second.periodic_runs == 1
    assert len(hourly.ticks) == 2
    assert len(broken.ticks) == 3
    assert len(kit.reporter.errors) == 3


def test_queued_job_is_retried_with_backoff_then_done() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=2)
    kit = build_worker(clock, [], {RUN_AUTOTESTS: operator})
    job_id = kit.queue.enqueue(
        RUN_AUTOTESTS,
        JobPayloadJson('{"assistant_version_id": "v1"}'),
        business_id=None,
    )

    kit.worker.run_once()
    failed_once = kit.job_repo.get(job_id)
    assert failed_once is not None
    assert failed_once.status is QueuedJobStatus.PENDING
    assert failed_once.attempts == 1
    assert failed_once.last_error == "ExternalServiceError: provider down"
    assert failed_once.lease_until is None and failed_once.lease_token is None

    clock.advance(10)
    kit.worker.run_once()
    assert len(operator.calls) == 1

    clock.advance(30)
    kit.worker.run_once()
    clock.advance(60)
    kit.worker.run_once()

    done = kit.job_repo.get(job_id)
    assert done is not None
    assert done.status is QueuedJobStatus.DONE
    assert done.lane is JobLane.DEFAULT
    assert len(operator.calls) == 3
    assert kit.reporter.errors == []


def test_queued_job_dies_after_max_attempts_or_without_handler() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=100)
    kit = build_worker(clock, [], {RUN_AUTOTESTS: operator})
    job_id = kit.queue.enqueue(
        RUN_AUTOTESTS,
        JobPayloadJson("{}"),
        business_id=None,
        lane=JobLane.AUTOTESTS,
    )
    orphan_id = kit.queue.enqueue(
        JobName("unknown_job"),
        JobPayloadJson("{}"),
        business_id=None,
    )

    for _ in range(10):
        kit.worker.run_once()
        clock.advance(10_000)

    dead = kit.job_repo.get(job_id)
    orphan = kit.job_repo.get(orphan_id)
    assert dead is not None and dead.status is QueuedJobStatus.DEAD
    assert dead.attempts == 5
    # Only the last attempt is marked final, so a handler can clean up then.
    assert [call.is_final_attempt for call in operator.calls] == [False] * 4 + [True]
    assert orphan is not None and orphan.status is QueuedJobStatus.DEAD
    assert orphan.last_error == "No handler for job unknown_job."
    assert kit.reporter.errors == []


def test_every_lane_is_drained_in_one_tick() -> None:
    clock = ControlledClock()
    operator = FlakyQueuedOperator(failures_before_success=0)
    kit = build_worker(clock, [], {RUN_AUTOTESTS: operator})
    for lane in JobLane:
        for _ in range(3):
            kit.queue.enqueue(
                RUN_AUTOTESTS, JobPayloadJson("{}"), business_id=None, lane=lane
            )

    report = kit.worker.run_once()

    assert (report.queued_runs, report.failures) == (12, 0)
    assert len(operator.calls) == 12
