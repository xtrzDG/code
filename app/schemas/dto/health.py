"""Readiness of an API instance: GET /readyz and the probes behind it."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.schemas.typings.maintenance.constrained_integers import DataTaskCount
from app.schemas.typings.platform.constrained_integers import (
    DatabaseConnectionCount,
    DatabasePoolSize,
    ElapsedMilliseconds,
    HeartbeatAgeSeconds,
    MigrationCount,
    PoolExhaustedSeconds,
)
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName


class DatabaseProbe(ImmutableDTO):
    """
    One look at the database: `select 1` within the probe's timeout, the
    migrations it has applied and how busy this process's pool is. SKIPPED
    without a database (storage in memory).
    """

    status: HealthCheckStatus
    failure: DatabaseProbeFailure | None = None
    latency: ElapsedMilliseconds | None = None
    applied_migrations: list[SchemaMigrationName] = Field(
        default_factory=list[SchemaMigrationName]
    )
    connections_in_use: DatabaseConnectionCount | None = None
    pool_size: DatabasePoolSize | None = None


class ReadinessQuery(ImmutableDTO):
    """Ask whether this instance should receive traffic."""


class DatabaseCheck(ImmutableDTO):
    """`select 1` answered in time (`latency_ms`), or why not."""

    status: HealthCheckStatus
    failure: DatabaseProbeFailure | None = None
    latency_ms: ElapsedMilliseconds | None = None


class MigrationsCheck(ImmutableDTO):
    """Every migration file of this build is applied (`pending` is 0)."""

    status: HealthCheckStatus
    pending: MigrationCount | None = None


class ConnectionPoolCheck(ImmutableDTO):
    """
    A database connection was free within the probe's timeout. When none
    was, `exhausted_seconds` says for how long every probe found the pool
    busy: DEGRADED at first (model calls and bursts pass), FAILED only past
    the readiness check's limit.
    """

    status: HealthCheckStatus
    in_use: DatabaseConnectionCount | None = None
    size: DatabasePoolSize | None = None
    exhausted_seconds: PoolExhaustedSeconds | None = None


class WorkerCheck(ImmutableDTO):
    """
    How old the freshest background worker pulse is. Reported, never a
    reason to stop traffic: an old or missing pulse is DEGRADED (jobs wait,
    requests are still answered).
    """

    status: HealthCheckStatus
    heartbeat_age_seconds: HeartbeatAgeSeconds | None = None
    release: ReleaseVersion | None = None


class DataTasksCheck(ImmutableDTO):
    """
    The post-deploy data tasks of this release that are not done yet
    (failed and stalled ones among them). Reported, never a reason to stop
    traffic: open tasks are DEGRADED. The deploy guard reads `open`.
    """

    status: HealthCheckStatus
    open: DataTaskCount | None = None
    failed: DataTaskCount | None = None
    stalled: DataTaskCount | None = None


class ReadinessChecks(ImmutableDTO):
    database: DatabaseCheck
    migrations: MigrationsCheck
    pool: ConnectionPoolCheck
    worker: WorkerCheck
    data_tasks: DataTasksCheck = DataTasksCheck(status=HealthCheckStatus.SKIPPED)


class ReadinessReport(ImmutableDTO):
    """READY when the database, the migrations and the pool are fine."""

    status: ReadinessState
    checks: ReadinessChecks
