"""
The timer of later jobs: each lane is woken once its job's due time has
passed (never before), a wake-up announced twice fires once, a sooner one
scheduled while the thread sleeps on a later one is not slept through, and
stopping drops what is pending.
"""

import threading

import pytest

from app.schemas.constants.jobs import JobLane
from app.utilities.jobs import job_wakeup_timer
from app.utilities.jobs.job_wakeup_timer import WAKE_MARGIN_SECONDS, JobWakeupTimer

DUE: int = 1_790_000_000_000_000
WAIT_SECONDS: float = 10.0


class SteppedClock:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.seconds: float = 100.0

    def __call__(self) -> float:
        return self.seconds


class RecordedWakes:
    def __init__(self) -> None:
        self.lanes: list[JobLane] = []
        self.woken: dict[JobLane, threading.Event] = {
            lane: threading.Event() for lane in JobLane
        }

    def __call__(self, lane: JobLane) -> None:
        self.lanes.append(lane)
        self.woken[lane].set()


def test_a_lane_is_woken_once_its_job_is_due_and_not_before() -> None:
    clock = SteppedClock()
    timer = JobWakeupTimer(RecordedWakes(), monotonic=clock)
    timer.schedule(JobLane.INBOUND, DUE, delay_seconds=3.0)

    lanes, wait_seconds = timer.take_due()
    assert lanes == []
    assert wait_seconds == pytest.approx(3.0 + WAKE_MARGIN_SECONDS)

    clock.seconds += 3.0
    assert timer.take_due()[0] == []
    clock.seconds += 2 * WAKE_MARGIN_SECONDS
    assert timer.take_due() == ([JobLane.INBOUND], None)
    assert timer.pending_count() == 0


def test_the_earliest_wakes_first_and_each_due_time_once() -> None:
    clock = SteppedClock()
    timer = JobWakeupTimer(RecordedWakes(), monotonic=clock)
    timer.schedule(JobLane.OUTBOUND, DUE + 5_000_000, delay_seconds=5.0)
    timer.schedule(JobLane.INBOUND, DUE, delay_seconds=1.0)
    # The same job announced again (NOTIFY reaches every listener once per
    # commit, but a job may be queued twice for one moment): one wake-up.
    assert timer.schedule(JobLane.INBOUND, DUE, delay_seconds=1.0)
    assert timer.pending_count() == 2

    clock.seconds += 2.0
    lanes, wait_seconds = timer.take_due()
    assert lanes == [JobLane.INBOUND]
    assert wait_seconds == pytest.approx(3.0 + WAKE_MARGIN_SECONDS)
    clock.seconds += 4.0
    assert timer.take_due() == ([JobLane.OUTBOUND], None)


def test_jobs_already_due_wake_at_once_and_one_lane_once() -> None:
    clock = SteppedClock()
    timer = JobWakeupTimer(RecordedWakes(), monotonic=clock)
    timer.schedule(JobLane.INBOUND, DUE - 2_000_000, delay_seconds=-2.0)
    timer.schedule(JobLane.INBOUND, DUE - 1_000_000, delay_seconds=-1.0)
    clock.seconds += 2 * WAKE_MARGIN_SECONDS

    assert timer.take_due() == ([JobLane.INBOUND], None)


def test_too_many_pending_wakeups_are_left_to_the_polls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(job_wakeup_timer, "MAX_PENDING_WAKEUPS", 2)
    timer = JobWakeupTimer(RecordedWakes(), monotonic=SteppedClock())

    assert timer.schedule(JobLane.INBOUND, DUE, 1.0)
    assert timer.schedule(JobLane.INBOUND, DUE + 1, 1.0)
    assert not timer.schedule(JobLane.INBOUND, DUE + 2, 1.0)
    assert timer.pending_count() == 2


def test_the_thread_wakes_a_sooner_lane_scheduled_while_it_sleeps() -> None:
    wakes = RecordedWakes()
    timer = JobWakeupTimer(wakes)
    timer.start()
    try:
        # The thread sleeps toward a wake-up a minute away ...
        timer.schedule(JobLane.AUTOTESTS, DUE + 60_000_000, delay_seconds=60.0)
        # ... and a job due now must not wait for it.
        timer.schedule(JobLane.INBOUND, DUE, delay_seconds=0.0)

        assert wakes.woken[JobLane.INBOUND].wait(WAIT_SECONDS)
        assert wakes.lanes == [JobLane.INBOUND]
        assert timer.pending_count() == 1
    finally:
        timer.stop()

    # Stopping drops the minute-away wake-up and ends the thread.
    assert timer.pending_count() == 0
    assert not wakes.woken[JobLane.AUTOTESTS].is_set()
    assert all(
        thread.name != job_wakeup_timer.TIMER_THREAD_NAME
        for thread in threading.enumerate()
    )


def test_a_stopped_timer_starts_again() -> None:
    wakes = RecordedWakes()
    timer = JobWakeupTimer(wakes)
    timer.start()
    timer.start()
    timer.stop()
    timer.start()
    try:
        timer.schedule(JobLane.OUTBOUND, DUE, delay_seconds=0.0)
        assert wakes.woken[JobLane.OUTBOUND].wait(WAIT_SECONDS)
    finally:
        timer.stop()
