import logging
import threading

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import PeriodicJobRunRepoContract, QueuedJobRepoContract
from app.gateways.worker.held_leases import HeldLeases, HeldPeriodicRun
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.schemas.dto.job_queue import (
    HeldJobLease,
    JobLeaseExtension,
    PeriodicRunLease,
)
from app.schemas.typings.platform.constrained_integers import JobLeaseSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# Leases are extended this many times per lease, so a slow database or a
# long pause still leaves room before another worker may take a job over.
BEATS_PER_LEASE: int = 4
HEARTBEAT_JOB_NAME: JobName = JobName("lease_heartbeat")


class LeaseHeartbeat:
    """
    Keeps the leases of everything this worker process runs alive: the
    queued jobs of the lane threads and the periodic job of the periodic
    thread. A lease that could not be extended was lost (the job ran past
    its lease and another worker took it over); the job finishes anyway,
    but its result is not stored.
    """

    def __init__(
        self,
        job_repo: QueuedJobRepoContract,
        periodic_run_repo: PeriodicJobRunRepoContract,
        held_leases: HeldLeases,
        wall_clock: WallClock[Microseconds],
        failure_reporter: JobFailureReporter,
        lease_seconds: JobLeaseSeconds,
    ) -> None:
        self._job_repo: QueuedJobRepoContract = job_repo
        self._periodic_run_repo: PeriodicJobRunRepoContract = periodic_run_repo
        self._held_leases: HeldLeases = held_leases
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._failure_reporter: JobFailureReporter = failure_reporter
        self._lease_seconds: JobLeaseSeconds = lease_seconds

    @property
    def interval_seconds(self) -> float:
        return int(self._lease_seconds) / BEATS_PER_LEASE

    def beat(self) -> None:
        """Extend every held lease to a full lease from now."""

        lease_until = Microseconds(
            int(self._wall_clock.now_unix())
            + int(self._lease_seconds) * MICROSECONDS_PER_SECOND
        )
        held_jobs: list[HeldJobLease] = self._held_leases.jobs()
        if held_jobs:
            extended: set[QueuedJobId] = set(
                self._job_repo.extend_leases(
                    JobLeaseExtension(leases=held_jobs, lease_until=lease_until)
                )
            )
            for lease in held_jobs:
                # A job that finished meanwhile is no longer held (the
                # runner lets go of it before it settles the job).
                if lease.job_id not in extended and self._held_leases.holds_job(
                    lease.job_id, lease.lease_token
                ):
                    LOGGER.warning("Job %s lost its lease", lease.job_id)

        for run in self._held_leases.periodic_runs():
            self._extend_periodic_run(run, lease_until)

    def run_forever(self, stop_event: threading.Event) -> None:
        """Beat every `interval_seconds` until stopped; failures are reported."""

        while not stop_event.wait(timeout=self.interval_seconds):
            try:
                self.beat()
            except Exception as error:  # noqa: BLE001 - keep beating
                self._failure_reporter.report(HEARTBEAT_JOB_NAME, error)

    def _extend_periodic_run(
        self,
        run: HeldPeriodicRun,
        lease_until: Microseconds,
    ) -> None:
        is_extended: bool = self._periodic_run_repo.extend_lease(
            PeriodicRunLease(
                job_name=run.job_name,
                period_key=run.period_key,
                lease_token=run.lease_token,
                lease_until=lease_until,
            )
        )
        if not is_extended:
            LOGGER.warning(
                "Periodic job %s (%s) lost its lease", run.job_name, run.period_key
            )
