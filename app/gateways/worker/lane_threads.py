import logging
import threading
import time
from collections.abc import Mapping

from app.contracts.jobs import JobWakeupContract
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.gateways.worker.queued_job_runner import QueuedJobRunner
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.constrained_integers import (
    JobClaimLimit,
    WorkerLaneConcurrency,
    WorkerLanePollSeconds,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobLeaseToken, JobName

LOGGER: logging.Logger = logging.getLogger(__name__)
ONE_JOB: JobClaimLimit = JobClaimLimit(1)
# After failed claims (the database is down) a thread waits longer and
# longer, up to this many seconds.
MAX_CLAIM_BACKOFF_SECONDS: int = 5 * 60


class LaneThreads:
    """
    The executors of the queued jobs: WORKER_LANE_CONCURRENCY threads per
    lane, each claiming and running one job at a time. A lane's threads
    only take jobs of their lane, so a long autotest run never holds up a
    customer message or a notification, and a busy lane never starves
    another. A thread with nothing to do waits for a wake-up (a job queued
    by any process, `JobWakeupContract`) or its lane's next poll, the
    safety net of a lost wake-up (WORKER_INBOUND_POLL_SECONDS for customer
    messages, WORKER_POLL_SECONDS for the rest). The threads of a lane
    start their polls spread over one interval, so they never poll in
    lockstep.

    Threads are daemons: on shutdown `join` waits a grace period for
    running jobs, then the process may exit; a job cut off this way is
    taken over by any worker once its lease ends.
    """

    def __init__(
        self,
        runner: QueuedJobRunner,
        lane_concurrency: Mapping[JobLane, WorkerLaneConcurrency],
        job_wakeup: JobWakeupContract,
        lane_poll_seconds: Mapping[JobLane, WorkerLanePollSeconds],
        failure_reporter: JobFailureReporter,
    ) -> None:
        self._runner: QueuedJobRunner = runner
        self._lane_concurrency: dict[JobLane, WorkerLaneConcurrency] = dict(
            lane_concurrency
        )
        self._job_wakeup: JobWakeupContract = job_wakeup
        self._lane_poll_seconds: dict[JobLane, WorkerLanePollSeconds] = dict(
            lane_poll_seconds
        )
        self._failure_reporter: JobFailureReporter = failure_reporter
        self._threads: list[threading.Thread] = []

    def start(self, stop_event: threading.Event) -> None:
        for lane in JobLane:
            concurrency: int = int(self._lane_concurrency.get(lane, 1))
            for index in range(concurrency):
                thread = threading.Thread(
                    target=self._work,
                    args=(lane, stop_event, index * self._poll_of(lane) / concurrency),
                    name=f"worker-{lane.value}-{index + 1}",
                    daemon=True,
                )
                thread.start()
                self._threads.append(thread)

        LOGGER.info(
            "Worker lanes started: %s",
            ", ".join(
                f"{lane.value}={int(self._lane_concurrency.get(lane, 1))}"
                for lane in JobLane
            ),
        )

    def wake_all(self) -> None:
        """Wake every idle thread (on shutdown, so they notice the stop)."""

        for lane in JobLane:
            self._job_wakeup.notify(lane)

    def join(self, timeout_seconds: float) -> bool:
        """Wait for the threads up to `timeout_seconds`; True when all ended."""

        deadline: float = time.monotonic() + timeout_seconds
        for thread in self._threads:
            thread.join(timeout=max(0.0, deadline - time.monotonic()))

        running: list[str] = [
            thread.name for thread in self._threads if thread.is_alive()
        ]
        if running:
            LOGGER.warning(
                "Jobs still running on %s; they continue on another worker "
                "once their lease ends",
                ", ".join(running),
            )

        return not running

    def _work(
        self,
        lane: JobLane,
        stop_event: threading.Event,
        first_poll_delay_seconds: float,
    ) -> None:
        # The first thread of a lane claims at once (jobs left from before a
        # restart); the others first wait their share of the poll interval
        # unless a job wakes them, so the lane's polls stay spread out.
        if first_poll_delay_seconds > 0:
            self._job_wakeup.wait(lane, first_poll_delay_seconds)

        poll_seconds: float = self._poll_of(lane)
        consecutive_failures: int = 0
        while not stop_event.is_set():
            try:
                jobs, lease_token = self._runner.claim(lane, ONE_JOB)
                consecutive_failures = 0
            except Exception as error:  # noqa: BLE001 - the queue may be unreachable
                consecutive_failures += 1
                self._failure_reporter.report(JobName(f"claim_{lane.value}"), error)
                stop_event.wait(
                    timeout=self._backoff_seconds(lane, consecutive_failures)
                )
                continue

            if jobs:
                self._run_all(jobs, lease_token)
                continue

            self._job_wakeup.wait(lane, poll_seconds)

    def _run_all(
        self, jobs: list[QueuedJobDocument], lease_token: JobLeaseToken
    ) -> None:
        for job in jobs:
            self._runner.run(job, lease_token)

    def _poll_of(self, lane: JobLane) -> float:
        return float(int(self._lane_poll_seconds[lane]))

    def _backoff_seconds(self, lane: JobLane, consecutive_failures: int) -> float:
        poll_seconds: int = int(self._lane_poll_seconds[lane])
        backoff_seconds: int = poll_seconds * (1 << min(consecutive_failures, 16))
        return float(min(backoff_seconds, max(poll_seconds, MAX_CLAIM_BACKOFF_SECONDS)))


def build_lane_poll_seconds(
    poll_seconds: WorkerPollSeconds,
    inbound_poll_seconds: WorkerLanePollSeconds | None,
) -> dict[JobLane, WorkerLanePollSeconds]:
    """
    How often each lane's idle threads look at the queue without a wake-up:
    customer messages every WORKER_INBOUND_POLL_SECONDS (when given, and
    never slower than the rest), the other lanes every WORKER_POLL_SECONDS.
    """

    regular = WorkerLanePollSeconds(int(poll_seconds))
    poll_by_lane: dict[JobLane, WorkerLanePollSeconds] = dict.fromkeys(JobLane, regular)
    if inbound_poll_seconds is not None:
        poll_by_lane[JobLane.INBOUND] = WorkerLanePollSeconds(
            min(int(inbound_poll_seconds), int(regular))
        )

    return poll_by_lane
