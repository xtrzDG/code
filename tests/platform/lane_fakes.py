"""Job operators that block and signal, for tests with real worker threads."""

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from app.gateways.worker.background_worker import BackgroundWorker
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.prefixed_id import QueuedJobId

# Upper bound of every wait in these tests; a passing test never waits long.
WAIT_SECONDS: float = 10.0


def wait_until(condition: Callable[[], bool], timeout: float = WAIT_SECONDS) -> bool:
    """Poll `condition` until it holds or the timeout passes."""

    deadline: float = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True

        time.sleep(0.01)

    return condition()


class SignallingPeriodicOperator:
    """Counts its ticks; the test waits for a number of them."""

    def __init__(self) -> None:
        self.ticks: list[JobTick] = []
        self.tick_times: list[float] = []

    def operate(self, input_data: JobTick) -> JobReport:
        self.ticks.append(input_data)
        self.tick_times.append(time.monotonic())
        return JobReport(processed_count=ProcessedItemCount(1))


class GatedQueuedOperator:
    """
    Every job blocks until the test opens its gate (or `max_seconds` pass,
    standing for a long autotest run); records which jobs run at once.
    """

    def __init__(self, max_seconds: float = 30.0, is_gated: bool = True) -> None:
        self.started: list[QueuedJobId] = []
        self.finished: list[QueuedJobId] = []
        self._max_seconds: float = max_seconds
        self._is_gated: bool = is_gated
        self._lock: threading.Lock = threading.Lock()
        self._gates: dict[QueuedJobId, threading.Event] = {}

    def operate(self, input_data: QueuedJobInput) -> JobReport:
        gate: threading.Event = self._gate(input_data.job_id)
        with self._lock:
            self.started.append(input_data.job_id)

        if self._is_gated:
            gate.wait(timeout=self._max_seconds)

        with self._lock:
            self.finished.append(input_data.job_id)

        return JobReport(processed_count=ProcessedItemCount(1))

    def running(self) -> set[QueuedJobId]:
        with self._lock:
            return set(self.started) - set(self.finished)

    def open(self, job_id: QueuedJobId) -> None:
        self._gate(job_id).set()

    def open_all(self) -> None:
        with self._lock:
            gates: list[threading.Event] = list(self._gates.values())

        for gate in gates:
            gate.set()
        self._is_gated = False

    def _gate(self, job_id: QueuedJobId) -> threading.Event:
        with self._lock:
            return self._gates.setdefault(job_id, threading.Event())


@contextmanager
def running_worker(
    worker: BackgroundWorker,
    on_exit: Callable[[], None] | None = None,
) -> Iterator[threading.Event]:
    """Run the worker in a thread for the block; stop and join it after."""

    stop_event = threading.Event()
    thread = threading.Thread(
        target=worker.run_forever,
        args=(stop_event,),
        name="test-worker",
        daemon=True,
    )
    thread.start()
    try:
        yield stop_event
    finally:
        if on_exit is not None:
            on_exit()

        stop_event.set()
        thread.join(timeout=WAIT_SECONDS)
        assert not thread.is_alive()
