"""Leases of queued jobs: heartbeats, lost leases and workers that die."""

import logging

import pytest

from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import JobLeaseExtension
from app.schemas.typings.platform.constrained_integers import (
    JobClaimLimit,
)
from app.schemas.typings.platform.constrained_strings import JobLeaseToken
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.job_runner_fakes import build_runner
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    FlakyQueuedOperator,
    build_job_stores,
    build_worker,
)


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


def test_a_job_that_finishes_during_a_beat_reports_no_lost_lease(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = FlakyQueuedOperator(failures_before_success=0)
    runner, _, heartbeat = build_runner(clock, stores, operator)
    build_worker(clock, [], stores=stores).queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None
    )
    claimed, lease_token = runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    extend_leases = stores.job_repo.extend_leases

    def finish_then_extend(extension: JobLeaseExtension) -> list[QueuedJobId]:
        # The job finishes after the beat saw it held, before its update.
        runner.run(claimed[0], lease_token)
        return extend_leases(extension)

    monkeypatch.setattr(stores.job_repo, "extend_leases", finish_then_extend)
    with caplog.at_level(logging.WARNING):
        heartbeat.beat()

    assert "lost its lease" not in caplog.text


def test_a_job_that_outlived_its_lease_leaves_the_result_to_the_new_holder(
    caplog: pytest.LogCaptureFixture,
) -> None:
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
    with caplog.at_level(logging.WARNING):
        heartbeat.beat()  # too late: the lease is gone
    assert "lost its lease" in caplog.text

    slow_runner.run(claimed[0], slow_token)

    job = stores.job_repo.get(job_id)
    assert job is not None
    assert job.status is QueuedJobStatus.DONE
    assert job.attempts == 2
    assert len(operator.calls) == 2
