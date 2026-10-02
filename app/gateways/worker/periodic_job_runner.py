import logging
from collections.abc import Sequence

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import PeriodicJobRunRepoContract
from app.gateways.worker.held_leases import (
    HeldLeases,
    HeldPeriodicRun,
    new_lease_token,
)
from app.gateways.worker.job_failure_reporter import JobFailureReporter, describe_error
from app.gateways.worker.periodic_job_spec import PeriodicJobSpec
from app.schemas.constants.jobs import PeriodicJobRunStatus
from app.schemas.domain.jobs import PeriodicJobRunDocument
from app.schemas.dto.job_queue import PeriodicRunStart
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import JobLeaseSeconds
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.utilities.jobs.periodic_runs import decide_periodic_run_start

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# A failed periodic job is retried after this long (or its own interval,
# when shorter) instead of waiting for its next period.
PERIODIC_RETRY_SECONDS: int = 5 * 60


class PeriodicJobRunner:
    """
    Runs the due periodic jobs one after another (reminders, retention
    purge, trials and grace periods, the journal flush).

    A job runs once per period across every worker and restart: the worker
    that claims the period's run (under a lease) runs it and records the
    outcome. A failed run is tried again after PERIODIC_RETRY_SECONDS by
    whichever worker comes first. Process-local jobs keep an in-memory
    schedule per process. Failures of one job never stop the others.
    """

    def __init__(
        self,
        periodic_jobs: Sequence[PeriodicJobSpec],
        periodic_run_repo: PeriodicJobRunRepoContract,
        wall_clock: WallClock[Microseconds],
        held_leases: HeldLeases,
        failure_reporter: JobFailureReporter,
        lease_seconds: JobLeaseSeconds,
    ) -> None:
        self._periodic_jobs: list[PeriodicJobSpec] = list(periodic_jobs)
        self._periodic_run_repo: PeriodicJobRunRepoContract = periodic_run_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._held_leases: HeldLeases = held_leases
        self._failure_reporter: JobFailureReporter = failure_reporter
        self._lease_seconds: JobLeaseSeconds = lease_seconds
        self._local_due_at: dict[JobName, int] = {}

    def run_due(self) -> tuple[int, int]:
        """Run every due job once: (runs, failures)."""

        runs: int = 0
        failures: int = 0
        for job in self._periodic_jobs:
            try:
                has_run, has_failed = (
                    self._run_local_job(job)
                    if job.is_process_local
                    else self._run_shared_job(job)
                )
            except Exception as error:  # noqa: BLE001 - e.g. the database is down
                has_run, has_failed = False, True
                self._failure_reporter.report(job.name, error)

            runs += int(has_run)
            failures += int(has_failed)

        return runs, failures

    def _run_shared_job(self, job: PeriodicJobSpec) -> tuple[bool, bool]:
        now: Microseconds = self._wall_clock.now_unix()
        period_key: JobPeriodKey = job.period_key(now)
        lease_token: JobLeaseToken = new_lease_token()
        run: PeriodicJobRunDocument | None = self._periodic_run_repo.claim(
            job.name,
            period_key,
            decide_periodic_run_start(
                PeriodicRunStart(
                    job_name=job.name,
                    period_key=period_key,
                    now=now,
                    lease_until=self._lease_end(now),
                    lease_token=lease_token,
                )
            ),
        )
        if run is None:
            return False, False

        held = HeldPeriodicRun(
            job_name=run.job_name,
            period_key=run.period_key,
            lease_token=lease_token,
        )
        self._held_leases.hold_periodic_run(held)
        try:
            report: JobReport = job.operator.operate(
                JobTick(job_name=job.name, scheduled_at=now)
            )
        except Exception as error:  # noqa: BLE001 - isolate job failures
            run.status = PeriodicJobRunStatus.FAILED
            run.last_error = describe_error(error)
            run.retry_at = Microseconds(
                int(self._wall_clock.now_unix()) + self._retry_delay(job)
            )
            self._finish(run, lease_token)
            self._failure_reporter.report(job.name, error)
            return True, True
        finally:
            self._held_leases.release_periodic_run(job.name)

        run.status = PeriodicJobRunStatus.SUCCEEDED
        run.processed_count = report.processed_count
        run.last_error = None
        self._finish(run, lease_token)
        LOGGER.info(
            "Periodic job %s (%s) processed %d items",
            job.name,
            run.period_key,
            report.processed_count,
        )
        return True, False

    def _run_local_job(self, job: PeriodicJobSpec) -> tuple[bool, bool]:
        now: int = int(self._wall_clock.now_unix())
        due_at: int | None = self._local_due_at.get(job.name)
        if due_at is not None and now < due_at:
            return False, False

        try:
            job.operator.operate(
                JobTick(job_name=job.name, scheduled_at=Microseconds(now))
            )
        except Exception as error:  # noqa: BLE001 - isolate job failures
            self._local_due_at[job.name] = now + self._retry_delay(job)
            self._failure_reporter.report(job.name, error)
            return True, True

        interval: int = int(job.interval_seconds) * MICROSECONDS_PER_SECOND
        self._local_due_at[job.name] = now + interval
        return True, False

    def _finish(self, run: PeriodicJobRunDocument, lease_token: JobLeaseToken) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        run.finished_at = now
        run.updated_at = now
        run.lease_until = None
        run.lease_token = None
        if not self._periodic_run_repo.finish(run, lease_token):
            LOGGER.warning(
                "Periodic job %s (%s) finished after its lease was lost",
                run.job_name,
                run.period_key,
            )

    def _retry_delay(self, job: PeriodicJobSpec) -> int:
        """Microseconds until a failed run is tried again."""

        return (
            min(int(job.interval_seconds), PERIODIC_RETRY_SECONDS)
            * MICROSECONDS_PER_SECOND
        )

    def _lease_end(self, now: Microseconds) -> Microseconds:
        return Microseconds(
            int(now) + int(self._lease_seconds) * MICROSECONDS_PER_SECOND
        )
