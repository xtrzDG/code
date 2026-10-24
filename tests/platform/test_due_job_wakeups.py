"""
Exact wake-ups of jobs queued for later: the queue announces a job's due
time (within EXACT_WAKEUP_HORIZON_SECONDS), a listening worker's signal
arms a timer for it, and a lane thread whose poll is a minute away takes
the job the moment it is due. Without a listening worker nothing is kept.
"""

import time

from typed_time_provider import Microseconds, WallClock

from app.facilitators.jobs.job_queue_facilitator import (
    EXACT_WAKEUP_HORIZON_SECONDS,
    JobQueueFacilitator,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.jobs.job_wakeup_payloads import (
    decode_job_wakeup,
    encode_job_wakeup,
)
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal
from tests.platform.lane_fakes import running_worker, wait_until
from tests.platform.worker_fakes import (
    ControlledClock,
    JobStores,
    build_job_stores,
    build_worker,
)

ANSWER_BURST: JobName = JobName("process_inbound_message")
PAYLOAD: JobPayloadJson = JobPayloadJson("{}")
SECOND: int = 1_000_000
# Polls a minute apart: a job taken within seconds was woken by its timer.
SLOW_POLL_SECONDS: int = 60


class RecordingSignal(JobWakeupSignal):
    def __init__(self) -> None:
        super().__init__()
        self.now: list[JobLane] = []
        self.later: list[tuple[JobLane, Microseconds]] = []

    def notify(self, lane: JobLane) -> None:
        self.now.append(lane)
        super().notify(lane)

    def notify_at(self, lane: JobLane, run_at: Microseconds) -> None:
        self.later.append((lane, run_at))
        super().notify_at(lane, run_at)


class RealTimeClock(ControlledClock):
    """The worker and the queue on real time, so a job really becomes due."""

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(preferred_time_unit_type=Microseconds)


class TimedOperator:
    """Remembers the wall-clock moment each job ran."""

    def __init__(self) -> None:
        self.ran_at: list[float] = []

    def operate(self, input_data: QueuedJobInput) -> JobReport:
        del input_data
        self.ran_at.append(time.time())
        return JobReport(processed_count=ProcessedItemCount(1))


def test_the_queue_announces_when_a_later_job_is_due() -> None:
    clock = ControlledClock()
    signal = RecordingSignal()
    stores = build_job_stores()
    queue = JobQueueFacilitator(
        job_repo=stores.job_repo, wall_clock=clock.wall_clock(), job_wakeup=signal
    )
    now: int = clock.nanoseconds // 1_000
    soon = Microseconds(now + 3 * SECOND)
    far = Microseconds(now + (EXACT_WAKEUP_HORIZON_SECONDS + 1) * SECOND)

    queue.enqueue(ANSWER_BURST, PAYLOAD, None, lane=JobLane.INBOUND)
    queue.enqueue(ANSWER_BURST, PAYLOAD, None, run_at=soon, lane=JobLane.INBOUND)
    queue.enqueue(ANSWER_BURST, PAYLOAD, None, run_at=far, lane=JobLane.DEFAULT)

    assert signal.now == [JobLane.INBOUND]
    # Far-off jobs are left to the polls.
    assert signal.later == [(JobLane.INBOUND, soon)]


def test_a_signal_nobody_listens_to_keeps_no_timer() -> None:
    signal = JobWakeupSignal()
    signal.notify_at(JobLane.INBOUND, Microseconds(0))

    assert not signal.has_listeners()
    assert signal.pending_wakeup_count() == 0
    assert not signal.wait(JobLane.INBOUND, 0.0)


def test_a_listening_signal_wakes_the_lane_when_its_job_is_due() -> None:
    clock = ControlledClock()
    signal = JobWakeupSignal(clock.wall_clock())
    with signal.listen(), signal.listen():
        # Due a minute from now on the wall clock: pending.
        later = Microseconds(clock.nanoseconds // 1_000 + 60 * SECOND)
        signal.notify_at(JobLane.OUTBOUND, later)
        # Already due: the lane is woken at once.
        signal.notify_at(JobLane.INBOUND, Microseconds(clock.nanoseconds // 1_000))

        assert signal.wait(JobLane.INBOUND, 10.0)
        assert signal.pending_wakeup_count() == 1

    # The last listener gone, the timer stops and drops the rest.
    assert not signal.has_listeners()
    assert signal.pending_wakeup_count() == 0


def test_a_lane_takes_a_later_job_the_moment_it_is_due() -> None:
    stores: JobStores = build_job_stores()
    operator = TimedOperator()
    kit = build_worker(
        RealTimeClock(),
        periodic_jobs=[],
        queued_operators={ANSWER_BURST: operator},
        stores=stores,
        poll_seconds=SLOW_POLL_SECONDS,
        inbound_poll_seconds=SLOW_POLL_SECONDS,
    )

    with running_worker(kit.worker):
        assert wait_until(stores.job_wakeup.has_listeners)
        run_at = Microseconds(time.time_ns() // 1_000 + SECOND // 2)
        kit.queue.enqueue(
            ANSWER_BURST, PAYLOAD, None, run_at=run_at, lane=JobLane.INBOUND
        )

        assert wait_until(lambda: len(operator.ran_at) == 1)

    # Not before it was due, and long before the next poll.
    assert operator.ran_at[0] >= int(run_at) / SECOND


def test_wakeup_payloads_name_the_lane_and_the_due_time() -> None:
    due = Microseconds(1_790_000_000_123_456)

    assert encode_job_wakeup(JobLane.INBOUND) == "inbound"
    assert encode_job_wakeup(JobLane.INBOUND, due) == "inbound@1790000000123456"
    assert decode_job_wakeup("inbound") == (JobLane.INBOUND, None)
    assert decode_job_wakeup("inbound@1790000000123456") == (JobLane.INBOUND, due)
    # Another release's lane, or a due time this release cannot read.
    assert decode_job_wakeup("bulk") is None
    assert decode_job_wakeup("inbound@soon") is None
    assert decode_job_wakeup("inbound@") is None
    assert decode_job_wakeup("inbound@-5") is None
