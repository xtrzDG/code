"""Time-triggered transport: runs periodic jobs and the leased job queue."""

import threading
from collections.abc import Mapping, Sequence

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import (
    JobWakeupContract,
    PeriodicJobRunRepoContract,
    QueuedJobOperator,
    QueuedJobRepoContract,
)
from app.contracts.observability import (
    ErrorReportingFacilitatorContract,
    JobMonitorFacilitatorContract,
)
from app.contracts.storage import StorageScopeContract
from app.facilitators.observability.null_job_monitor_facilitator import (
    NullJobMonitorFacilitator,
)
from app.gateways.worker.heartbeat_recorder import WorkerHeartbeatRecorder
from app.gateways.worker.held_leases import HeldLeases
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.gateways.worker.job_telemetry import NO_JOB_TELEMETRY, JobTelemetry
from app.gateways.worker.lane_threads import LaneThreads, build_lane_poll_seconds
from app.gateways.worker.lease_heartbeat import LeaseHeartbeat
from app.gateways.worker.periodic_job_runner import PeriodicJobRunner
from app.gateways.worker.periodic_job_spec import PeriodicJobSpec
from app.gateways.worker.queued_job_rounds import JOB_QUEUE_JOB, run_due_queued_jobs
from app.gateways.worker.queued_job_runner import QueuedJobRunner
from app.gateways.worker.tick_pacing import tick_pause_seconds, wait_reaping
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import (
    JobLeaseSeconds,
    ProcessedItemCount,
    WorkerLaneConcurrency,
    WorkerLanePollSeconds,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName

__all__ = ["BackgroundWorker", "PeriodicJobSpec", "WorkerTickReport"]

# A claimed job is reserved this long without a heartbeat; the heartbeat
# extends it every quarter of that while the job runs.
DEFAULT_LEASE_SECONDS: JobLeaseSeconds = JobLeaseSeconds(120)
# On shutdown running jobs get this long to finish (Render stops a service
# 30 s after SIGTERM); the rest go back to the queue for another worker.
STOP_GRACE_SECONDS: float = 25.0
WORKER_TICK_JOB: JobName = JobName("worker_tick")


class WorkerTickReport(ImmutableDTO):
    """What one scheduler tick did."""

    periodic_runs: ProcessedItemCount
    queued_runs: ProcessedItemCount
    failures: ProcessedItemCount


class BackgroundWorker:
    """
    Runs periodic jobs (reminders, retention purge, grace periods, journal
    flush) and queued jobs (autotests, retries; later customer messages and
    deliveries) with exponential backoff. Any number of worker processes may
    run next to each other:

    - queued jobs are claimed with a lease (FOR UPDATE SKIP LOCKED on
      Postgres), so each runs once; a heartbeat keeps the leases of running
      jobs alive, and the reaper releases the jobs of a worker that died
      (every tick, and between ticks as often as the worker's quickest
      lane polls), waking the lanes that can take them;
    - every lane has its own threads (WORKER_LANE_CONCURRENCY), so a long
      autotest run never delays a reminder or a customer reply, and jobs
      with the same serial key (the autotests of one business) run one at a
      time;
    - a worker serves the lanes of its role (WORKER_LANES, every lane by
      default): the workers that answer customers take `inbound` and
      `outbound`, a batch worker `default` and `autotests`, so no batch job
      can take down the process that answers customers;
    - periodic jobs run on their own thread, once per period (day, ISO
      week or interval) across workers and restarts; a worker runs the
      shared ones of its lanes, and every worker its process-local ones.

    A queued job of one business runs in that business's storage scope.
    Failures of one job never stop others, and a storage outage never stops
    the worker: the tick is reported and the next one comes after a growing
    pause. Unexpected errors go to the error reporter. Every tick of the
    periodic thread writes the worker's heartbeat (GET /readyz reports its
    age), and periodic runs check in with the job monitor (Sentry Crons).
    """

    def __init__(
        self,
        periodic_jobs: Sequence[PeriodicJobSpec],
        queued_job_operators: Mapping[JobName, QueuedJobOperator],
        job_repo: QueuedJobRepoContract,
        periodic_run_repo: PeriodicJobRunRepoContract,
        wall_clock: WallClock[Microseconds],
        error_reporter: ErrorReportingFacilitatorContract,
        poll_seconds: WorkerPollSeconds,
        storage_scope: StorageScopeContract,
        job_wakeup: JobWakeupContract,
        lane_concurrency: Mapping[JobLane, WorkerLaneConcurrency],
        lease_seconds: JobLeaseSeconds = DEFAULT_LEASE_SECONDS,
        job_monitor: JobMonitorFacilitatorContract | None = None,
        heartbeat_recorder: WorkerHeartbeatRecorder | None = None,
        inbound_poll_seconds: WorkerLanePollSeconds | None = None,
        lanes: Sequence[JobLane] = tuple(JobLane),
        stop_grace_seconds: float = STOP_GRACE_SECONDS,
        job_telemetry: JobTelemetry = NO_JOB_TELEMETRY,
    ) -> None:
        self._poll_seconds: WorkerPollSeconds = poll_seconds
        self._stop_grace_seconds: float = stop_grace_seconds
        self._lanes: tuple[JobLane, ...] = tuple(lanes)
        self._job_wakeup: JobWakeupContract = job_wakeup
        self._heartbeat_recorder: WorkerHeartbeatRecorder | None = heartbeat_recorder
        self._lane_concurrency: dict[JobLane, WorkerLaneConcurrency] = dict(
            lane_concurrency
        )
        self._failure_reporter = JobFailureReporter(error_reporter)
        held_leases = HeldLeases()
        self._queued_runner = QueuedJobRunner(
            queued_job_operators=queued_job_operators,
            job_repo=job_repo,
            wall_clock=wall_clock,
            storage_scope=storage_scope,
            held_leases=held_leases,
            failure_reporter=self._failure_reporter,
            lease_seconds=lease_seconds,
            telemetry=job_telemetry,
        )
        self._periodic_runner = PeriodicJobRunner(
            periodic_jobs=[
                job
                for job in periodic_jobs
                if job.is_process_local or job.lane in self._lanes
            ],
            periodic_run_repo=periodic_run_repo,
            wall_clock=wall_clock,
            held_leases=held_leases,
            failure_reporter=self._failure_reporter,
            lease_seconds=lease_seconds,
            job_monitor=(
                NullJobMonitorFacilitator() if job_monitor is None else job_monitor
            ),
        )
        self._heartbeat = LeaseHeartbeat(
            job_repo=job_repo,
            periodic_run_repo=periodic_run_repo,
            held_leases=held_leases,
            wall_clock=wall_clock,
            failure_reporter=self._failure_reporter,
            lease_seconds=lease_seconds,
        )
        lane_poll_seconds = build_lane_poll_seconds(poll_seconds, inbound_poll_seconds)
        self._reap_seconds: float = min(
            (float(int(lane_poll_seconds[lane])) for lane in self._lanes),
            default=float(int(poll_seconds)),
        )
        self._lane_threads = LaneThreads(
            runner=self._queued_runner,
            lane_concurrency=self._lane_concurrency,
            job_wakeup=job_wakeup,
            lane_poll_seconds=lane_poll_seconds,
            failure_reporter=self._failure_reporter,
            lanes=self._lanes,
        )

    def run_once(self) -> WorkerTickReport:
        """
        One tick in the calling thread: release expired leases, run every
        due periodic job, then every due queued job of the worker's lanes. For
        tests and one-off runs: no heartbeat runs meanwhile, so a batch
        that takes longer than a lease may be taken over by another worker.
        """

        maintenance_failures: int = self._release_expired_leases()
        periodic_runs, periodic_failures = self._periodic_runner.run_due()
        self._beat()
        queued_runs, queued_failures = self._run_due_queued_jobs()
        return WorkerTickReport(
            periodic_runs=ProcessedItemCount(periodic_runs),
            queued_runs=ProcessedItemCount(queued_runs),
            failures=ProcessedItemCount(
                maintenance_failures + periodic_failures + queued_failures
            ),
        )

    def run_queued_jobs(self) -> WorkerTickReport:
        """
        The queue only, in the calling thread: release expired leases, then
        run every due queued job of the worker's lanes (jobs they queue for now
        too). For tests and one-off runs, like `run_once`.
        """

        maintenance_failures: int = self._release_expired_leases()
        queued_runs, queued_failures = self._run_due_queued_jobs()
        return WorkerTickReport(
            periodic_runs=ProcessedItemCount(0),
            queued_runs=ProcessedItemCount(queued_runs),
            failures=ProcessedItemCount(maintenance_failures + queued_failures),
        )

    def run_periodic_tick(self) -> tuple[int, int]:
        """The periodic thread's tick: reaper, due periodic jobs, heartbeat."""

        maintenance_failures: int = self._release_expired_leases()
        runs, failures = self._periodic_runner.run_due()
        self._beat()
        return runs, maintenance_failures + failures

    def run_forever(self, stop_event: threading.Event) -> None:
        """
        Listen for the wake-ups of every process (jobs queued by the API),
        start the lane threads and the heartbeat, then tick periodic jobs in
        the calling thread until `stop_event` is set. A tick that fails as a
        whole is reported and followed by a pause that doubles with every
        further failure (at most MAX_TICK_BACKOFF_SECONDS). On stop, running
        jobs get STOP_GRACE_SECONDS to finish; the rest are handed back.
        """

        with self._job_wakeup.listen():
            self._run_threads(stop_event)

    def _run_threads(self, stop_event: threading.Event) -> None:
        # The lane threads and the heartbeat stop with their own event, set
        # once the periodic loop is over (also when it fails).
        stopping = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat.run_forever,
            args=(stopping,),
            name="worker-lease-heartbeat",
            daemon=True,
        )
        heartbeat_thread.start()
        if self._heartbeat_recorder is not None:
            self._heartbeat_recorder.start()
        self._lane_threads.start(stopping)
        try:
            self._tick_periodic_jobs(stop_event)
        finally:
            stopping.set()
            self._lane_threads.wake_all()
            if not self._lane_threads.join(self._stop_grace_seconds):
                self._hand_back_running_jobs()

    def _hand_back_running_jobs(self) -> None:
        try:
            self._queued_runner.hand_back_running_jobs()
        except Exception as error:  # noqa: BLE001 - their leases end anyway
            self._failure_reporter.report(JOB_QUEUE_JOB, error)

    def _tick_periodic_jobs(self, stop_event: threading.Event) -> None:
        consecutive_failures: int = 0
        while not stop_event.is_set():
            try:
                self.run_periodic_tick()
                consecutive_failures = 0
            except Exception as error:  # noqa: BLE001 - the worker must survive
                consecutive_failures += 1
                self._failure_reporter.report(WORKER_TICK_JOB, error)

            pause: int = tick_pause_seconds(
                int(self._poll_seconds), consecutive_failures
            )
            if consecutive_failures:
                stop_event.wait(timeout=pause)
            else:
                wait_reaping(
                    stop_event, pause, self._reap_seconds, self._release_expired_leases
                )

    def _beat(self) -> None:
        if self._heartbeat_recorder is not None:
            self._heartbeat_recorder.beat(self._periodic_runner.last_results())

    def _release_expired_leases(self) -> int:
        """The reaper; the lanes of the jobs it put back are woken (any worker)."""

        try:
            for lane in self._queued_runner.release_expired_leases():
                self._job_wakeup.notify(lane)
        except Exception as error:  # noqa: BLE001 - the queue may be unreachable
            self._failure_reporter.report(JOB_QUEUE_JOB, error)
            return 1

        return 0

    def _run_due_queued_jobs(self) -> tuple[int, int]:
        return run_due_queued_jobs(
            self._queued_runner,
            self._lanes,
            self._lane_concurrency,
            self._failure_reporter,
        )
