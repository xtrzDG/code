import logging
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.platform_safety import PeriodicJobHeartbeatRepoContract
from app.contracts.storage import StorageScopeContract
from app.gateways.worker.periodic_job_spec import PeriodicJobSpec
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.domain.jobs import PeriodicJobResult
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName, ReleaseVersion
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# A job is missed once it has not succeeded for its interval plus this
# grace (at least; a quarter of a longer interval): a slow tick, a retry
# after a failure or a deploy is no missed run.
MIN_GRACE_SECONDS: int = 30 * 60
# The heartbeat of a job this release does not know, overdue this long,
# is a job a deploy removed: a starting worker forgets it, so removed
# jobs never crowd the alert's read of the overdue ones.
REMOVED_JOB_AFTER_SECONDS: int = 7 * 24 * 60 * 60
MAX_REMOVED_READ: DocumentQueryLimit = DocumentQueryLimit(100)


def job_run_allowance(interval_seconds: JobIntervalSeconds) -> int:
    """Microseconds a job may go without a success: interval plus grace."""

    interval: int = int(interval_seconds)
    return (interval + max(MIN_GRACE_SECONDS, interval // 4)) * MICROSECONDS_PER_SECOND


class PeriodicJobHeartbeats:
    """
    The heartbeats of the shared periodic jobs (`periodic_job_heartbeats`),
    the missed-run alert's source that needs no Sentry. When the worker
    starts it registers every shared job it knows (also those of lanes it
    does not serve: a lane no worker serves is a missed run too), stamping
    its release and keeping what earlier workers recorded, and forgets the
    heartbeats of jobs it does not know that are overdue for a week (jobs
    a deploy removed); after every
    tick it records the jobs that succeeded since (`record`, from the
    periodic runner's last results), keeping the release a registration
    stamped. A heartbeat that cannot be written is logged and skipped: the
    next tick tries again.
    """

    def __init__(
        self,
        periodic_jobs: Sequence[PeriodicJobSpec],
        heartbeat_repo: PeriodicJobHeartbeatRepoContract,
        storage_scope: StorageScopeContract,
        release: ReleaseVersion | None,
    ) -> None:
        self._jobs: dict[JobName, PeriodicJobSpec] = {
            job.name: job for job in periodic_jobs if not job.is_process_local
        }
        self._repo: PeriodicJobHeartbeatRepoContract = heartbeat_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._release: ReleaseVersion | None = release
        self._recorded: dict[JobName, Microseconds] = {}

    def register(self, now: Microseconds) -> None:
        try:
            with self._storage_scope.platform_wide():
                stored: dict[JobName, PeriodicJobHeartbeatDocument] = {
                    heartbeat.job_name: heartbeat
                    for heartbeat in self._repo.get_many(list(self._jobs))
                }
                for name, job in self._jobs.items():
                    self._repo.save(self._registered(job, stored.get(name), now))
                self._forget_removed_jobs(now)
        except ApplicationError as error:
            LOGGER.warning("Periodic job heartbeats were not registered: %s", error)

    def _forget_removed_jobs(self, now: Microseconds) -> None:
        long_ago = Microseconds(
            int(now) - REMOVED_JOB_AFTER_SECONDS * MICROSECONDS_PER_SECOND
        )
        for heartbeat in self._repo.list_overdue(long_ago, MAX_REMOVED_READ):
            if heartbeat.job_name not in self._jobs and heartbeat.release != (
                self._release
            ):
                self._repo.delete(heartbeat.job_name)
                LOGGER.info(
                    "Forgot the heartbeat of removed periodic job %s",
                    heartbeat.job_name,
                )

    def record(self, results: Sequence[PeriodicJobResult]) -> None:
        succeeded: list[PeriodicJobResult] = [
            result
            for result in results
            if result.job_name in self._jobs
            and result.outcome is PeriodicJobOutcome.SUCCEEDED
            and self._recorded.get(result.job_name) != result.finished_at
        ]
        if not succeeded:
            return

        try:
            with self._storage_scope.platform_wide():
                stored: dict[JobName, PeriodicJobHeartbeatDocument] = {
                    heartbeat.job_name: heartbeat
                    for heartbeat in self._repo.get_many(
                        [result.job_name for result in succeeded]
                    )
                }
                for result in succeeded:
                    self._repo.save(
                        self._succeeded(
                            self._jobs[result.job_name],
                            stored.get(result.job_name),
                            result.finished_at,
                        )
                    )
                    self._recorded[result.job_name] = result.finished_at
        except ApplicationError as error:
            LOGGER.warning("Periodic job heartbeats were not written: %s", error)

    def _registered(
        self,
        job: PeriodicJobSpec,
        stored: PeriodicJobHeartbeatDocument | None,
        now: Microseconds,
    ) -> PeriodicJobHeartbeatDocument:
        if stored is None:
            return PeriodicJobHeartbeatDocument(
                job_name=job.name,
                interval_seconds=job.interval_seconds,
                lane=job.lane,
                release=self._release,
                registered_at=now,
                due_by=Microseconds(int(now) + job_run_allowance(job.interval_seconds)),
                created_at=now,
                updated_at=now,
            )

        # A changed interval counts from the last success (else from now).
        since: int = (
            int(now)
            if stored.last_succeeded_at is None
            else int(stored.last_succeeded_at)
        )
        due_by: int = (
            int(stored.due_by)
            if stored.interval_seconds == job.interval_seconds
            else since + job_run_allowance(job.interval_seconds)
        )
        return stored.model_copy(
            update={
                "interval_seconds": job.interval_seconds,
                "lane": job.lane,
                "release": self._release,
                "due_by": Microseconds(due_by),
                "updated_at": now,
            }
        )

    def _succeeded(
        self,
        job: PeriodicJobSpec,
        stored: PeriodicJobHeartbeatDocument | None,
        finished_at: Microseconds,
    ) -> PeriodicJobHeartbeatDocument:
        # Only a registration stamps the release: an old worker still
        # running during a deploy must not take a job back from the new
        # release (its alert would then never see the job missed).
        return PeriodicJobHeartbeatDocument(
            job_name=job.name,
            interval_seconds=job.interval_seconds,
            lane=job.lane,
            release=self._release if stored is None else stored.release,
            registered_at=finished_at if stored is None else stored.registered_at,
            last_succeeded_at=finished_at,
            due_by=Microseconds(
                int(finished_at) + job_run_allowance(job.interval_seconds)
            ),
            created_at=finished_at if stored is None else stored.created_at,
            updated_at=finished_at,
        )
