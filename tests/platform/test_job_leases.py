"""Leases of queued jobs: heartbeats, lost leases and workers that die."""

import logging

import pytest

from app.gateways.worker.held_leases import HeldLeases
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.gateways.worker.lease_heartbeat import LeaseHeartbeat
from app.gateways.worker.queued_job_runner import QueuedJobRunner
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.constrained_integers import (
    JobClaimLimit,
    JobLeaseSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobLeaseToken
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    FlakyQueuedOperator,
    JobStores,
    RecordingErrorReporter,
    build_job_stores,
    build_worker,
)

LEASE: JobLeaseSeconds = JobLeaseSeconds(120)


def build_runner(
    clock: ControlledClock,
    stores: JobStores,
    operator: FlakyQueuedOperator,
) -> tuple[QueuedJobRunner, HeldLeases, LeaseHeartbeat]:
    held_leases = HeldLeases()
    reporter = JobFailureReporter(RecordingErrorReporter())
    runner = QueuedJobRunner(
        queued_job_operators={RUN_AUTOTESTS: operator},
        job_repo=stores.job_repo,
        wall_clock=clock.wall_clock(),
        storage_scope=StorageScopeContext(),
        held_leases=held_leases,
        failure_reporter=reporter,
        lease_seconds=LEASE,
    )
    heartbeat = LeaseHeartbeat(
        job_repo=stores.job_repo,
        periodic_run_repo=stores.periodic_run_repo,
        held_leases=held_leases,
        wall_clock=clock.wall_clock(),
        failure_reporter=reporter,
        lease_seconds=LEASE,
    )
    return runner, held_leases, heartbeat


def test_a_job_whose_worker_died_runs_again_on_another_worker() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    survivor = build_worker(clock, [], {RUN_AUTOTESTS: operator}, stores=stores)
    job_id = survivor.queue.enqueue(RUN_AUTOTESTS, JobPayloadJson("{}"), None)
    crashed_runner, _, _ = build_runner(clock, stores, operator)
    claimed, crashed_token = crashed_runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    assert [job.id for job in claimed] == [job_id]  # and then the process died

    while_leased = survivor.worker.run_once()
    clock.advance(121)
    after_lease = survivor.worker.run_once()

    assert while_leased.queued_runs == 0
    assert after_lease.queued_runs == 1
    done = stores.job_repo.get(job_id)
    assert done is not None
    assert done.status is QueuedJobStatus.DONE
    assert done.attempts == 2  # the crashed attempt counts
    # The crashed worker cannot overwrite the result if it comes back.
    claimed[0].status = QueuedJobStatus.DEAD
    assert not stores.job_repo.settle(claimed[0], crashed_token)


def test_the_heartbeat_keeps_a_long_job_leased() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    runner, held_leases, heartbeat = build_runner(clock, stores, operator)
    job_id = build_worker(clock, [], stores=stores).queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None
    )
    claimed, lease_token = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    other = build_worker(clock, [], {RUN_AUTOTESTS: operator}, stores=stores)

    for _ in range(10):  # a 10-minute job with a beat every minute
        clock.advance(60)
        heartbeat.beat()
        assert other.worker.run_once().queued_runs == 0

    leased = stores.job_repo.get(job_id)
    assert leased is not None
    assert leased.status is QueuedJobStatus.RUNNING
    assert held_leases.jobs()[0].lease_token == lease_token

    outcome = runner.run(claimed[0], lease_token)

    assert (outcome.has_run, outcome.has_failed) == (True, False)
    assert held_leases.jobs() == []
    done = stores.job_repo.get(job_id)
    assert done is not None and done.status is QueuedJobStatus.DONE
    assert done.lease_until is None and done.lease_token is None


def test_a_heartbeat_while_a_job_is_settled_reports_no_lost_lease(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    runner, held_leases, heartbeat = build_runner(clock, stores, operator)
    build_worker(clock, [], stores=stores).queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None
    )
    claimed, lease_token = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    settle = stores.job_repo.settle

    def settle_then_beat(job: QueuedJobDocument, token: JobLeaseToken) -> bool:
        settled = settle(job, token)
        heartbeat.beat()  # the heartbeat thread's turn comes right now
        return settled

    monkeypatch.setattr(stores.job_repo, "settle", settle_then_beat)
    with caplog.at_level(logging.WARNING):
        outcome = runner.run(claimed[0], lease_token)

    assert (outcome.has_run, outcome.has_failed) == (True, False)
    assert held_leases.jobs() == []
    assert "lost its lease" not in caplog.text


def test_a_job_that_outlived_its_lease_leaves_the_result_to_the_new_holder() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    slow_runner, _, heartbeat = build_runner(clock, stores, operator)
    job_id = build_worker(clock, [], stores=stores).queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None
    )
    claimed, slow_token = slow_runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    clock.advance(121)  # no heartbeat came through (the database was away)
    fast = build_worker(clock, [], {RUN_AUTOTESTS: operator}, stores=stores)
    fast.worker.run_once()
    heartbeat.beat()  # too late: the lease is gone

    slow_runner.run(claimed[0], slow_token)

    job = stores.job_repo.get(job_id)
    assert job is not None
    assert job.status is QueuedJobStatus.DONE
    assert job.attempts == 2
    assert len(operator.calls) == 2


def test_jobs_whose_last_attempt_lost_its_worker_die() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    runner, _, _ = build_runner(clock, stores, operator)
    job_id = build_worker(clock, [], stores=stores).queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None
    )

    for _ in range(5):
        claimed, _ = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
        assert len(claimed) == 1
        clock.advance(121)
        runner.release_expired_leases()

    dead = stores.job_repo.get(job_id)
    assert dead is not None
    assert dead.status is QueuedJobStatus.DEAD
    assert dead.attempts == 5
    assert dead.last_error is not None and "Lease expired" in str(dead.last_error)
    assert operator.calls == []
