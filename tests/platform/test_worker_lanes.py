"""
Worker roles (WORKER_LANES): a worker runs only the queued and shared
periodic jobs of its lanes, so the workers that answer customers never run
a batch job; every worker still runs its process-local jobs, and jobs of
other lanes wait for the worker of their role.
"""

import logging
import threading

import pytest

from app.contracts.jobs import QueuedJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.lane_fakes import (
    GatedQueuedOperator,
    SignallingPeriodicOperator,
    running_worker,
    wait_until,
)
from tests.platform.worker_fakes import (
    ControlledClock,
    WorkerKit,
    build_job_stores,
    build_worker,
)

CUSTOMER_LANES: tuple[JobLane, ...] = (JobLane.INBOUND, JobLane.OUTBOUND)
BATCH_LANES: tuple[JobLane, ...] = (JobLane.DEFAULT, JobLane.AUTOTESTS)
JOB_OF_LANE: dict[JobLane, JobName] = {
    JobLane.INBOUND: JobName("process_inbound_message"),
    JobLane.OUTBOUND: JobName("deliver_outbound"),
    JobLane.DEFAULT: JobName("run_business_export"),
    JobLane.AUTOTESTS: JobName("run_autotests"),
}
EMPTY_PAYLOAD: JobPayloadJson = JobPayloadJson("{}")
HOUR: JobIntervalSeconds = JobIntervalSeconds(3600)


def status_of(kit: WorkerKit, job_id: QueuedJobId) -> QueuedJobStatus:
    job = kit.job_repo.get(job_id)
    assert job is not None
    return job.status


def test_each_role_runs_only_the_queued_jobs_of_its_lanes() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    operator = GatedQueuedOperator(is_gated=False)
    operators: dict[JobName, QueuedJobOperator] = dict.fromkeys(
        JOB_OF_LANE.values(), operator
    )
    customer = build_worker(clock, [], operators, stores=stores, lanes=CUSTOMER_LANES)
    batch = build_worker(clock, [], operators, stores=stores, lanes=BATCH_LANES)
    jobs: dict[JobLane, QueuedJobId] = {
        lane: customer.queue.enqueue(name, EMPTY_PAYLOAD, None, lane=lane)
        for lane, name in JOB_OF_LANE.items()
    }

    customer_tick = customer.worker.run_queued_jobs()

    assert int(customer_tick.queued_runs) == 2
    assert {lane: status_of(customer, job) for lane, job in jobs.items()} == {
        JobLane.INBOUND: QueuedJobStatus.DONE,
        JobLane.OUTBOUND: QueuedJobStatus.DONE,
        JobLane.DEFAULT: QueuedJobStatus.PENDING,
        JobLane.AUTOTESTS: QueuedJobStatus.PENDING,
    }

    batch_tick = batch.worker.run_queued_jobs()

    assert int(batch_tick.queued_runs) == 2
    assert {status_of(batch, job) for job in jobs.values()} == {QueuedJobStatus.DONE}


def test_shared_periodic_jobs_run_with_the_role_of_their_lane() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    reminders = SignallingPeriodicOperator()
    digest = SignallingPeriodicOperator()
    customer_flush = SignallingPeriodicOperator()
    batch_flush = SignallingPeriodicOperator()

    def specs(flush: SignallingPeriodicOperator) -> list[PeriodicJobSpec]:
        return [
            PeriodicJobSpec(
                name=JobName("send_booking_reminders"),
                interval_seconds=HOUR,
                operator=reminders,
                lane=JobLane.OUTBOUND,
            ),
            PeriodicJobSpec(
                name=JobName("send_value_reports"),
                interval_seconds=HOUR,
                operator=digest,
            ),
            # Each process flushes its own buffer, whatever its role.
            PeriodicJobSpec(
                name=JobName("flush_llm_traces"),
                interval_seconds=HOUR,
                operator=flush,
                is_process_local=True,
            ),
        ]

    customer = build_worker(
        clock, specs(customer_flush), stores=stores, lanes=CUSTOMER_LANES
    )
    batch = build_worker(clock, specs(batch_flush), stores=stores, lanes=BATCH_LANES)

    customer.worker.run_once()
    batch.worker.run_once()
    # The next tick in the same hour: every shared job ran once.
    customer.worker.run_once()
    batch.worker.run_once()

    assert len(reminders.ticks) == 1
    assert len(digest.ticks) == 1
    assert len(customer_flush.ticks) == 1
    assert len(batch_flush.ticks) == 1


def test_a_worker_starts_threads_only_for_its_lanes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app.gateways.worker.lane_threads")
    clock = ControlledClock()
    operator = GatedQueuedOperator(is_gated=False)
    kit = build_worker(
        clock,
        [],
        dict.fromkeys(JOB_OF_LANE.values(), operator),
        lanes=CUSTOMER_LANES,
    )
    inbound = kit.queue.enqueue(
        JOB_OF_LANE[JobLane.INBOUND], EMPTY_PAYLOAD, None, lane=JobLane.INBOUND
    )
    export = kit.queue.enqueue(
        JOB_OF_LANE[JobLane.DEFAULT], EMPTY_PAYLOAD, None, lane=JobLane.DEFAULT
    )

    before: set[threading.Thread] = set(threading.enumerate())
    with running_worker(kit.worker):
        assert wait_until(lambda: status_of(kit, inbound) is QueuedJobStatus.DONE)
        # The lanes start one after another, so the inbound job can be done
        # before the next lane's thread exists; the log line follows them all.
        assert wait_until(lambda: "Worker lanes started" in caplog.text)
        lane_threads: set[str] = {
            thread.name.rsplit("-", 1)[0]
            for thread in set(threading.enumerate()) - before
            if thread.name.startswith("worker-") and thread.name[-1].isdigit()
        }

    assert lane_threads == {"worker-inbound", "worker-outbound"}
    assert status_of(kit, export) is QueuedJobStatus.PENDING
    assert operator.started == [inbound]
