import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.health import (
    DatabaseProbeAdapterContract,
    WorkerHeartbeatRepoContract,
)
from app.contracts.storage import (
    SchemaMigrationSourceAdapterContract,
    StorageScopeContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.health import (
    ConnectionPoolCheck,
    DatabaseCheck,
    DatabaseProbe,
    MigrationsCheck,
    ReadinessChecks,
    ReadinessQuery,
    ReadinessReport,
    WorkerCheck,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import (
    HeartbeatAgeSeconds,
    MigrationCount,
)
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# A worker writes its pulse on every tick (WORKER_POLL_SECONDS, 15 s by
# default); one long periodic job may delay a few. Older than this, jobs are
# probably waiting.
WORKER_HEARTBEAT_STALE_SECONDS: int = 5 * 60
SERVING_STATUSES: frozenset[HealthCheckStatus] = frozenset(
    {HealthCheckStatus.OK, HealthCheckStatus.SKIPPED}
)


class CheckReadinessUseCase(UseCaseContract[ReadinessQuery, ReadinessReport]):
    """
    Whether this API instance should receive traffic (GET /readyz):

    - the database answers `select 1` in time;
    - every migration file of this build is applied (a newer database is
      fine: during a deploy the old release runs on the new schema);
    - a pool connection was free within the probe's timeout;
    - the freshest worker pulse is reported with its age, never a reason to
      stop traffic (DEGRADED when it is old or missing).

    Without a database the first three are SKIPPED. Never raises.
    """

    def __init__(
        self,
        database_probe: DatabaseProbeAdapterContract,
        migration_source: SchemaMigrationSourceAdapterContract,
        worker_heartbeat_repo: WorkerHeartbeatRepoContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._database_probe: DatabaseProbeAdapterContract = database_probe
        self._migration_source: SchemaMigrationSourceAdapterContract = migration_source
        self._worker_heartbeat_repo: WorkerHeartbeatRepoContract = worker_heartbeat_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._expected_migrations: list[SchemaMigrationName] | None = None

    def run(self, input_data: ReadinessQuery) -> ReadinessReport:
        del input_data
        probe: DatabaseProbe = self._database_probe.probe()
        checks = ReadinessChecks(
            database=DatabaseCheck(
                status=probe.status, failure=probe.failure, latency_ms=probe.latency
            ),
            migrations=self._check_migrations(probe),
            pool=ConnectionPoolCheck(
                status=pool_status(probe),
                in_use=probe.connections_in_use,
                size=probe.pool_size,
            ),
            worker=self._check_worker(),
        )
        is_ready: bool = all(
            check.status in SERVING_STATUSES
            for check in (checks.database, checks.migrations, checks.pool)
        )
        return ReadinessReport(
            status=ReadinessState.READY if is_ready else ReadinessState.NOT_READY,
            checks=checks,
        )

    def _check_migrations(self, probe: DatabaseProbe) -> MigrationsCheck:
        if probe.status is not HealthCheckStatus.OK:
            return MigrationsCheck(status=probe.status)

        try:
            expected: list[SchemaMigrationName] = self._load_expected_migrations()
        except ApplicationError as error:
            LOGGER.error("Migration files cannot be read: %s", error)
            return MigrationsCheck(status=HealthCheckStatus.FAILED)

        applied: set[SchemaMigrationName] = set(probe.applied_migrations)
        pending: int = sum(1 for name in expected if name not in applied)
        return MigrationsCheck(
            status=HealthCheckStatus.OK if pending == 0 else HealthCheckStatus.FAILED,
            pending=MigrationCount(pending),
        )

    def _load_expected_migrations(self) -> list[SchemaMigrationName]:
        """The migration files of this build, read once (they never change)."""

        if self._expected_migrations is None:
            self._expected_migrations = [
                script.name for script in self._migration_source.load_scripts()
            ]

        return self._expected_migrations

    def _check_worker(self) -> WorkerCheck:
        try:
            with self._storage_scope.platform_wide():
                heartbeat: WorkerHeartbeatDocument | None = (
                    self._worker_heartbeat_repo.find_freshest()
                )
        except ApplicationError as error:
            LOGGER.warning("Worker heartbeats cannot be read: %s", error)
            return WorkerCheck(status=HealthCheckStatus.DEGRADED)

        if heartbeat is None:
            return WorkerCheck(status=HealthCheckStatus.DEGRADED)

        age_seconds: int = max(
            0,
            (int(self._wall_clock.now_unix()) - int(heartbeat.beat_at))
            // MICROSECONDS_PER_SECOND,
        )
        return WorkerCheck(
            status=(
                HealthCheckStatus.OK
                if age_seconds <= WORKER_HEARTBEAT_STALE_SECONDS
                else HealthCheckStatus.DEGRADED
            ),
            heartbeat_age_seconds=HeartbeatAgeSeconds(age_seconds),
            release=heartbeat.release,
        )


def pool_status(probe: DatabaseProbe) -> HealthCheckStatus:
    """FAILED only when no connection came free in time; the rest is the probe's."""

    if probe.failure is DatabaseProbeFailure.POOL_EXHAUSTED:
        return HealthCheckStatus.FAILED

    if probe.status is HealthCheckStatus.SKIPPED:
        return HealthCheckStatus.SKIPPED

    return HealthCheckStatus.OK
