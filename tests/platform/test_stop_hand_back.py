"""
A worker that stops while a job still runs past the grace period (a
deploy) hands the job back: due at once for the next worker, its cut-off
attempt not counted and no lost lease, so deploys never make a job look
like one that kills its worker.
"""

from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.lane_fakes import GatedQueuedOperator, running_worker, wait_until
from tests.platform.worker_fakes import (
    RUN_AUTOTESTS,
    ControlledClock,
    build_job_stores,
    build_worker,
)


def test_a_stopping_worker_hands_its_running_job_to_the_next_one() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    stuck = GatedQueuedOperator(max_seconds=30.0)
    stopping = build_worker(
        clock, [], {RUN_AUTOTESTS: stuck}, stores=stores, stop_grace_seconds=0.05
    )
    job_id = stopping.queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None, lane=JobLane.AUTOTESTS
    )

    with running_worker(stopping.worker):
        assert wait_until(lambda: stuck.started == [job_id])
    handed_back = stores.job_repo.get(job_id)
    assert handed_back is not None
    assert handed_back.status is QueuedJobStatus.PENDING
    assert int(handed_back.attempts) == 0
    assert int(handed_back.lost_leases) == 0
    assert handed_back.lease_token is None
    assert handed_back.run_at == clock.wall_clock().now_unix()

    # The cut-off run ends after all: its result is not written.
    stuck.open(job_id)
    assert wait_until(lambda: stuck.finished == [job_id])
    assert stores.job_repo.get(job_id) == handed_back

    successor = GatedQueuedOperator(is_gated=False)
    next_worker = build_worker(clock, [], {RUN_AUTOTESTS: successor}, stores=stores)
    next_worker.worker.run_queued_jobs()

    done = stores.job_repo.get(job_id)
    assert done is not None
    assert done.status is QueuedJobStatus.DONE
    assert int(done.attempts) == 1
    assert successor.finished == [job_id]


def test_a_job_that_ends_within_the_grace_period_is_not_handed_back() -> None:
    clock = ControlledClock()
    quick = GatedQueuedOperator(is_gated=False)
    kit = build_worker(clock, [], {RUN_AUTOTESTS: quick}, stop_grace_seconds=5.0)
    job_id = kit.queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), None, lane=JobLane.AUTOTESTS
    )

    with running_worker(kit.worker):
        assert wait_until(lambda: quick.finished == [job_id])

    done = kit.job_repo.get(job_id)
    assert done is not None
    assert done.status is QueuedJobStatus.DONE
