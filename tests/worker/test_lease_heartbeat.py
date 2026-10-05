"""
The lease heartbeat of a worker process: it keeps every lease the process
holds alive while it runs, reports a beat that failed and keeps beating,
says which leases were lost, and stops with the worker. A job whose lease
was lost is processed by its new holder once; the old holder's late result
(even a failure that would schedule a retry) is not stored.
"""

import logging
import threading

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.in_memory_queued_job_claim_adapter import (
    InMemoryQueuedJobClaimAdapter,
)
from app.gateways.worker.held_leases import HeldLeases, HeldPeriodicRun
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.gateways.worker.lease_heartbeat import LeaseHeartbeat
from app.gateways.worker.queued_job_runner import QueuedJobRunner
from app.repositories.job_repositories import QueuedJobRepository
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import JobLeaseExtension, PeriodicRunStart
from app.schemas.typings.platform.constrained_integers import (
    JobClaimLimit,
    JobLeaseSeconds,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.jobs.periodic_runs import decide_periodic_run_start
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
MICROSECONDS_PER_SECOND: int = 1_000_000


class CountedStop(threading.Event):
    """A stop event that lets `beats` waits pass, then is set: no real waiting."""

    def __init__(self, beats: int) -> None:
        super().__init__()
        self.waits: list[float | None] = []
        self._left: int = beats

    def wait(self, timeout: float | None = None) -> bool:
        self.waits.append(timeout)
        if self._left == 0:
            self.set()
            return True
        self._left -= 1
        return False


class FirstBeatFails(QueuedJobRepository):
    """The in-memory job queue whose first lease extension cannot reach the database."""

    failures_left: int = 1

    def extend_leases(self, extension: JobLeaseExtension) -> list[QueuedJobId]:
        if self.failures_left > 0:
            self.failures_left -= 1
            raise RuntimeError("the database went away")
        return super().extend_leases(extension)


def flaky_job_stores() -> tuple[JobStores, FirstBeatFails]:
    stores = build_job_stores()
    jobs = InMemoryDocumentCollectionAdapter[QueuedJobDocument](QueuedJobDocument)
    flaky = FirstBeatFails(jobs, InMemoryQueuedJobClaimAdapter(jobs))
    return JobStores(flaky, stores.periodic_run_repo, stores.job_wakeup), flaky


class Process:
    """One worker process's runner, held leases and heartbeat."""

    def __init__(
        self, clock: ControlledClock, stores: JobStores, operator: FlakyQueuedOperator
    ) -> None:
        self.held = HeldLeases()
        self.errors = RecordingErrorReporter()
        reporter = JobFailureReporter(self.errors)
        self.runner = QueuedJobRunner(
            queued_job_operators={RUN_AUTOTESTS: operator},
            job_repo=stores.job_repo,
            wall_clock=clock.wall_clock(),
            storage_scope=StorageScopeContext(),
            held_leases=self.held,
            failure_reporter=reporter,
            lease_seconds=LEASE,
        )
        self.heartbeat = LeaseHeartbeat(
            job_repo=stores.job_repo,
            periodic_run_repo=stores.periodic_run_repo,
            held_leases=self.held,
            wall_clock=clock.wall_clock(),
            failure_reporter=reporter,
            lease_seconds=LEASE,
        )


def queue_job(clock: ControlledClock, stores: JobStores) -> QueuedJobId:
    return build_worker(clock, [], stores=stores).queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None
    )


def lease_end(stores: JobStores, job_id: QueuedJobId) -> int:
    job = stores.job_repo.get(job_id)
    assert job is not None and job.lease_until is not None
    return int(job.lease_until)


def test_the_heartbeat_beats_four_times_a_lease_until_the_worker_stops() -> None:
    clock, stores = ControlledClock(), build_job_stores()
    process = Process(clock, stores, FlakyQueuedOperator(0))
    job_id = queue_job(clock, stores)
    process.runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    clock.advance(30)
    stop = CountedStop(beats=3)

    process.heartbeat.run_forever(stop)

    assert stop.waits == [30.0, 30.0, 30.0, 30.0]
    assert (
        lease_end(stores, job_id)
        == clock.nanoseconds // 1_000 + 120 * MICROSECONDS_PER_SECOND
    )


def test_a_stopped_worker_beats_no_more() -> None:
    clock, stores = ControlledClock(), build_job_stores()
    process = Process(clock, stores, FlakyQueuedOperator(0))
    job_id = queue_job(clock, stores)
    process.runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    claimed_until = lease_end(stores, job_id)
    clock.advance(60)

    process.heartbeat.run_forever(CountedStop(beats=0))

    assert lease_end(stores, job_id) == claimed_until


def test_a_failed_beat_is_reported_and_the_next_one_keeps_the_lease() -> None:
    clock = ControlledClock()
    stores, flaky = flaky_job_stores()
    process = Process(clock, stores, FlakyQueuedOperator(0))
    job_id = queue_job(clock, stores)
    process.runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    clock.advance(40)

    process.heartbeat.run_forever(CountedStop(beats=2))

    assert [str(error) for error in process.errors.errors] == ["the database went away"]
    assert flaky.failures_left == 0
    assert (
        lease_end(stores, job_id)
        == clock.nanoseconds // 1_000 + 120 * MICROSECONDS_PER_SECOND
    )


def test_a_lost_lease_leaves_the_job_to_its_new_holder_who_runs_it_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock, stores = ControlledClock(), build_job_stores()
    stale_operator = FlakyQueuedOperator(failures_before_success=1)
    stale = Process(clock, stores, stale_operator)
    job_id = queue_job(clock, stores)
    claimed, stale_token = stale.runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    clock.advance(121)  # the database was away: no beat came through
    holder_operator = FlakyQueuedOperator(failures_before_success=0)
    holder = build_worker(clock, [], {RUN_AUTOTESTS: holder_operator}, stores=stores)
    assert holder.worker.run_once().queued_runs == 1

    with caplog.at_level(logging.WARNING):
        stale.heartbeat.beat()
    # The stale worker's run fails late; its retry must not undo the result.
    outcome = stale.runner.run(claimed[0], stale_token)
    clock.advance(3_600)

    assert f"Job {job_id} lost its lease" in caplog.text
    assert (outcome.has_run, outcome.has_failed) == (True, True)
    done = stores.job_repo.get(job_id)
    assert done is not None and done.status is QueuedJobStatus.DONE
    assert holder.worker.run_once().queued_runs == 0
    assert len(holder_operator.calls) == 1
    assert stale.held.jobs() == []


def test_a_lost_periodic_lease_is_reported_and_the_others_stay_held(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock, stores = ControlledClock(), build_job_stores()
    process = Process(clock, stores, FlakyQueuedOperator(0))
    lost = HeldPeriodicRun(
        job_name=JobName("send_digests"),
        period_key=JobPeriodKey("2026-09-21"),
        lease_token=JobLeaseToken("0" * 32),
    )
    process.held.hold_periodic_run(lost)
    job_id = queue_job(clock, stores)
    process.runner.claim(JobLane.DEFAULT, JobClaimLimit(1))
    clock.advance(30)

    with caplog.at_level(logging.WARNING):
        process.heartbeat.beat()

    assert "Periodic job send_digests (2026-09-21) lost its lease" in caplog.text
    assert (
        lease_end(stores, job_id)
        == clock.nanoseconds // 1_000 + 120 * MICROSECONDS_PER_SECOND
    )


def test_a_held_periodic_run_is_extended_and_nothing_else_is_touched() -> None:
    clock, stores = ControlledClock(), build_job_stores()
    process = Process(clock, stores, FlakyQueuedOperator(0))
    now = clock.wall_clock().now_unix()
    run = HeldPeriodicRun(
        job_name=JobName("send_digests"),
        period_key=JobPeriodKey("2026-09-21"),
        lease_token=JobLeaseToken("1" * 32),
    )
    claimed = stores.periodic_run_repo.claim(
        run.job_name,
        run.period_key,
        decide_periodic_run_start(
            PeriodicRunStart(
                job_name=run.job_name,
                period_key=run.period_key,
                now=now,
                lease_until=Microseconds(int(now) + 120 * MICROSECONDS_PER_SECOND),
                lease_token=run.lease_token,
            )
        ),
    )
    assert claimed is not None
    process.held.hold_periodic_run(run)
    clock.advance(30)

    process.heartbeat.beat()  # no queued job is held: only the periodic run

    stored = stores.periodic_run_repo.get(run.job_name, run.period_key)
    assert stored is not None and stored.lease_until is not None
    assert (
        int(stored.lease_until)
        == clock.nanoseconds // 1_000 + 120 * MICROSECONDS_PER_SECOND
    )
