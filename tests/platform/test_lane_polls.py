"""
The lane threads' safety-net polls: customer messages are looked for every
WORKER_INBOUND_POLL_SECONDS, the other lanes every WORKER_POLL_SECONDS, the
threads of a lane start spread over one interval (never in lockstep), and
the worker listens for other processes' wake-ups while its lanes run.
"""

import threading
import time
from collections.abc import Generator
from contextlib import contextmanager

from app.gateways.worker.background_worker import BackgroundWorker
from app.gateways.worker.lane_threads import build_lane_poll_seconds
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import (
    WorkerLanePollSeconds,
    WorkerPollSeconds,
)
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.lane_fakes import running_worker, wait_until
from tests.platform.worker_fakes import (
    TEST_LANE_CONCURRENCY,
    ControlledClock,
    RecordingErrorReporter,
    build_job_stores,
)


class RecordingWakeup(JobWakeupSignal):
    """The in-process signal, remembering every wait and the listening."""

    def __init__(self) -> None:
        super().__init__()
        self.waits: list[tuple[str, JobLane, float]] = []
        self.is_listening: bool = False
        self.listened: int = 0
        self._lock: threading.Lock = threading.Lock()

    def wait(self, lane: JobLane, timeout_seconds: float) -> bool:
        with self._lock:
            self.waits.append((threading.current_thread().name, lane, timeout_seconds))

        return super().wait(lane, min(timeout_seconds, 0.05))

    @contextmanager
    def listen(self) -> Generator[None]:
        self.is_listening = True
        self.listened += 1
        try:
            yield
        finally:
            self.is_listening = False

    def first_waits(self, lane: JobLane) -> dict[str, float]:
        """The first wait of every thread of `lane`, by thread name."""

        firsts: dict[str, float] = {}
        with self._lock:
            for thread_name, waited_lane, timeout in self.waits:
                if waited_lane is lane:
                    firsts.setdefault(thread_name, timeout)

        return firsts


class StopMissingWakeup(JobWakeupSignal):
    """
    The in-process signal whose stop wake-ups never arrive: a sibling
    thread of the lane took and cleared each of them.
    """

    def __init__(self) -> None:
        super().__init__()
        self.lost: set[JobLane] = set()
        self._waiting: dict[str, JobLane] = {}
        self._lock: threading.Lock = threading.Lock()

    def notify(self, lane: JobLane) -> None:
        if lane in self.lost:
            self.lost.discard(lane)
            return

        super().notify(lane)

    def wait(self, lane: JobLane, timeout_seconds: float) -> bool:
        with self._lock:
            self._waiting[threading.current_thread().name] = lane
        try:
            return super().wait(lane, timeout_seconds)
        finally:
            with self._lock:
                del self._waiting[threading.current_thread().name]

    def every_lane_waits(self) -> bool:
        with self._lock:
            return set(self._waiting.values()) == set(JobLane)


def build_listening_worker(wakeup: JobWakeupSignal) -> BackgroundWorker:
    stores = build_job_stores()
    return BackgroundWorker(
        periodic_jobs=[],
        queued_job_operators={},
        job_repo=stores.job_repo,
        periodic_run_repo=stores.periodic_run_repo,
        wall_clock=ControlledClock().wall_clock(),
        error_reporter=RecordingErrorReporter(),
        poll_seconds=WorkerPollSeconds(12),
        storage_scope=StorageScopeContext(),
        job_wakeup=wakeup,
        lane_concurrency=TEST_LANE_CONCURRENCY,
        inbound_poll_seconds=WorkerLanePollSeconds(2),
    )


def test_customer_messages_are_polled_more_often_than_the_rest() -> None:
    polls = build_lane_poll_seconds(WorkerPollSeconds(15), WorkerLanePollSeconds(2))

    assert polls == {
        JobLane.INBOUND: WorkerLanePollSeconds(2),
        JobLane.OUTBOUND: WorkerLanePollSeconds(15),
        JobLane.DEFAULT: WorkerLanePollSeconds(15),
        JobLane.AUTOTESTS: WorkerLanePollSeconds(15),
        JobLane.OPS: WorkerLanePollSeconds(15),
    }
    # Never slower than the other lanes, and the same without its own value.
    capped = build_lane_poll_seconds(WorkerPollSeconds(5), WorkerLanePollSeconds(30))
    assert capped[JobLane.INBOUND] == WorkerLanePollSeconds(5)
    unset = build_lane_poll_seconds(WorkerPollSeconds(7), None)
    assert set(unset.values()) == {WorkerLanePollSeconds(7)}


def test_a_lanes_threads_start_their_polls_spread_over_one_interval() -> None:
    wakeup = RecordingWakeup()
    worker = build_listening_worker(wakeup)

    with running_worker(worker):
        assert wait_until(lambda: len(wakeup.first_waits(JobLane.AUTOTESTS)) == 2)
        assert wait_until(lambda: len(wakeup.first_waits(JobLane.INBOUND)) == 2)

    # Thread 1 claims at once and then waits a whole interval; thread 2
    # first waits half of one, so the two never poll together.
    autotests = wakeup.first_waits(JobLane.AUTOTESTS)
    assert sorted(autotests.values()) == [6.0, 12.0]
    inbound = wakeup.first_waits(JobLane.INBOUND)
    assert sorted(inbound.values()) == [1.0, 2.0]
    assert inbound["worker-inbound-2"] == 1.0
    # A lane of one thread polls on its whole interval.
    assert set(wakeup.first_waits(JobLane.OUTBOUND).values()) == {12.0}


def test_the_worker_listens_while_its_lanes_run() -> None:
    wakeup = RecordingWakeup()
    worker = build_listening_worker(wakeup)

    with running_worker(worker):
        assert wait_until(lambda: wakeup.is_listening)

    assert not wakeup.is_listening
    assert wakeup.listened == 1


def test_an_in_process_signal_has_nothing_to_listen_to() -> None:
    wakeup = JobWakeupSignal()

    with wakeup.listen():
        wakeup.notify(JobLane.INBOUND)

    assert wakeup.wait(JobLane.INBOUND, 0.0)
    wakeup.notify_all()
    assert all(wakeup.wait(lane, 0.0) for lane in JobLane)
    assert not wakeup.wait(JobLane.INBOUND, 0.0)


def test_threads_that_missed_the_stops_wake_up_still_stop_at_once() -> None:
    wakeup = StopMissingWakeup()
    worker = build_listening_worker(wakeup)
    stop_event = threading.Event()
    thread = threading.Thread(target=worker.run_forever, args=(stop_event,))
    thread.start()
    assert wait_until(wakeup.every_lane_waits)

    wakeup.lost = set(JobLane)
    stop_event.set()
    stopping_at: float = time.monotonic()
    thread.join(timeout=10.0)

    # Woken again by the shutdown, not by their polls 12 seconds away.
    assert not thread.is_alive()
    assert time.monotonic() - stopping_at < 5.0
    assert wakeup.lost == set()
