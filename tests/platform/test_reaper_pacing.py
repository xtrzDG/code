"""
The reaper of a worker that answers customers runs between ticks as often
as its quickest lane polls, and wakes the lane of every job it puts back:
a job whose worker died is due within moments of its lease's end, not up
to a whole WORKER_POLL_SECONDS later.
"""

import threading

from app.gateways.worker.tick_pacing import tick_pause_seconds, wait_reaping
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.typings.platform.constrained_integers import JobClaimLimit
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.platform.job_runner_fakes import build_runner
from tests.platform.worker_fakes import (
    ControlledClock,
    CountingStopEvent,
    FlakyQueuedOperator,
    build_job_stores,
    build_worker,
)

CUSTOMER_LANES: tuple[JobLane, ...] = (JobLane.INBOUND, JobLane.OUTBOUND)
BATCH_LANES: tuple[JobLane, ...] = (JobLane.DEFAULT, JobLane.AUTOTESTS)
CUSTOMER_MESSAGE: JobName = JobName("process_inbound_message")


class RecordingStopEvent(threading.Event):
    """Records every wait without sleeping; set after `stop_after_waits`."""

    def __init__(self, stop_after_waits: int | None = None) -> None:
        super().__init__()
        self.pauses: list[float | None] = []
        self._stop_after_waits: int | None = stop_after_waits

    def wait(self, timeout: float | None = None) -> bool:
        self.pauses.append(timeout)
        if (
            self._stop_after_waits is not None
            and len(self.pauses) >= self._stop_after_waits
        ):
            self.set()

        return self.is_set()


def test_the_pause_between_ticks_doubles_after_failed_ticks() -> None:
    assert tick_pause_seconds(5, 0) == 5
    assert tick_pause_seconds(5, 1) == 10
    assert tick_pause_seconds(5, 3) == 40
    assert tick_pause_seconds(15, 10) == 300
    assert tick_pause_seconds(400, 1) == 400


def test_the_reaper_runs_between_two_ticks() -> None:
    stop_event = RecordingStopEvent()
    reaps: list[int] = []

    wait_reaping(stop_event, 15, 2, lambda: reaps.append(1))

    assert stop_event.pauses == [2, 2, 2, 2, 2, 2, 2, 1]
    assert len(reaps) == 7


def test_a_stop_ends_the_wait_without_another_reap() -> None:
    stop_event = RecordingStopEvent(stop_after_waits=3)
    reaps: list[int] = []

    wait_reaping(stop_event, 15, 2, lambda: reaps.append(1))

    assert stop_event.pauses == [2, 2, 2]
    assert len(reaps) == 2


def test_without_a_quicker_lane_the_pause_is_one_wait() -> None:
    stop_event = RecordingStopEvent()
    reaps: list[int] = []

    wait_reaping(stop_event, 15, 15, lambda: reaps.append(1))

    assert stop_event.pauses == [15]
    assert reaps == []


def test_a_customer_worker_reaps_at_its_inbound_poll() -> None:
    kit = build_worker(
        ControlledClock(),
        [],
        poll_seconds=15,
        inbound_poll_seconds=2,
        lanes=CUSTOMER_LANES,
        stop_grace_seconds=1,
    )
    stop_event = CountingStopEvent(ticks=10)

    kit.worker.run_forever(stop_event)

    # Tick, seven reaps two seconds apart, the last second, the next tick.
    assert stop_event.pauses == [2, 2, 2, 2, 2, 2, 2, 1, 2, 2]


def test_a_batch_worker_reaps_once_a_tick() -> None:
    kit = build_worker(
        ControlledClock(),
        [],
        poll_seconds=15,
        inbound_poll_seconds=2,
        lanes=BATCH_LANES,
        stop_grace_seconds=1,
    )
    stop_event = CountingStopEvent(ticks=3)

    kit.worker.run_forever(stop_event)

    assert stop_event.pauses == [15, 15, 15]


def test_the_reaper_wakes_the_lane_of_a_job_it_put_back() -> None:
    clock = ControlledClock()
    stores = build_job_stores()
    kit = build_worker(clock, [], stores=stores, lanes=CUSTOMER_LANES)
    job_id = kit.queue.enqueue(
        CUSTOMER_MESSAGE, JobPayloadJson("{}"), None, lane=JobLane.INBOUND
    )
    crashed_runner, _, _ = build_runner(
        clock, stores, FlakyQueuedOperator(failures_before_success=0)
    )
    claimed, _ = crashed_runner.claim(JobLane.INBOUND, JobClaimLimit(1))
    assert [job.id for job in claimed] == [job_id]  # and then its worker died
    stores.job_wakeup.wait(JobLane.INBOUND, 0)  # the enqueue's own signal

    clock.advance(121)
    kit.worker.run_periodic_tick()

    released = stores.job_repo.get(job_id)
    assert released is not None
    assert released.status is QueuedJobStatus.PENDING
    assert stores.job_wakeup.wait(JobLane.INBOUND, 0)
    assert not stores.job_wakeup.wait(JobLane.OUTBOUND, 0)
