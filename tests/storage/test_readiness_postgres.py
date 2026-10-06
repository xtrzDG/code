"""The readiness probe and the worker pulses on a real Postgres."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import cast

import psycopg
from psycopg import errors as database_errors
from typed_time_provider import Microseconds

from app.adapters.health.postgres_database_probe_adapter import (
    PostgresDatabaseProbeAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.repositories.worker_heartbeat_repository import WorkerHeartbeatRepository
from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.health import ReadinessQuery
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.observability.check_readiness_use_case import (
    CheckReadinessUseCase,
)
from app.utilities.observability.readiness_memory import ReadinessMemory
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.data_tasks.data_task_support import data_task_states, no_data_tasks
from tests.platform.readiness_fakes import heartbeat_at
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY, build_fixed_wall_clock

SECOND: int = 1_000_000


def migration_count() -> int:
    return len(SqlFileMigrationSourceAdapter(MIGRATIONS_DIRECTORY).load_scripts())


def test_a_migrated_database_answers_with_every_migration_applied(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    probe = PostgresDatabaseProbeAdapter(connection_pool).probe()

    assert probe.status is HealthCheckStatus.OK
    assert probe.latency is not None
    assert len(probe.applied_migrations) == migration_count()
    assert probe.pool_size == 8
    assert probe.connections_in_use == 0


def test_a_database_without_migrations_is_not_ready(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    pool = PostgresConnectionPoolClient(
        postgres_server.app_database_url(empty_database_name), max_size=2
    )
    try:
        use_case = CheckReadinessUseCase(
            database_probe=PostgresDatabaseProbeAdapter(pool),
            migration_source=SqlFileMigrationSourceAdapter(MIGRATIONS_DIRECTORY),
            worker_heartbeat_repo=EmptyHeartbeats(),
            storage_scope=StorageScopeContext(),
            wall_clock=build_fixed_wall_clock(),
            memory=ReadinessMemory(),
            data_task_registry=no_data_tasks(),
            data_task_state_repo=data_task_states(),
        )
        report = use_case.run(ReadinessQuery())
    finally:
        pool.close()

    assert report.status is ReadinessState.NOT_READY
    assert report.checks.database.status is HealthCheckStatus.OK
    assert report.checks.migrations.pending == migration_count()


def test_a_pool_with_every_connection_borrowed_is_exhausted(
    database_url: DatabaseUrl,
) -> None:
    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    probe_adapter = PostgresDatabaseProbeAdapter(pool, timeout_seconds=0.2)
    try:
        with pool.connection():
            probe = probe_adapter.probe()
        after = probe_adapter.probe()
    finally:
        pool.close()

    assert probe.status is HealthCheckStatus.FAILED
    assert probe.failure is DatabaseProbeFailure.POOL_EXHAUSTED
    assert probe.connections_in_use == 1
    assert after.status is HealthCheckStatus.OK


def test_a_server_that_is_down_is_unreachable() -> None:
    pool = PostgresConnectionPoolClient(
        DatabaseUrl("postgresql://workshop@127.0.0.1:1/workshop"), max_size=2
    )

    probe = PostgresDatabaseProbeAdapter(pool, timeout_seconds=0.5).probe()

    assert probe.status is HealthCheckStatus.FAILED
    assert probe.failure is DatabaseProbeFailure.UNREACHABLE


class FailingPool:
    """Hands out a connection whose queries fail with one psycopg error."""

    max_size: int = 4

    def __init__(self, error: psycopg.Error) -> None:
        self._error: psycopg.Error = error

    def open_connection_count(self) -> int:
        return 1

    def idle_connection_count(self) -> int:
        return 1

    @contextmanager
    def connection(
        self, acquire_timeout_seconds: float | None = None
    ) -> Generator[PostgresConnection]:
        del acquire_timeout_seconds
        raise self._error
        yield cast(PostgresConnection, None)  # pragma: no cover


def test_server_errors_are_told_apart() -> None:
    def probe_failure(error: psycopg.Error) -> DatabaseProbeFailure | None:
        pool = cast(PostgresConnectionPoolClient, FailingPool(error))
        return PostgresDatabaseProbeAdapter(pool).probe().failure

    assert probe_failure(database_errors.QueryCanceled()) is (
        DatabaseProbeFailure.TIMEOUT
    )
    assert probe_failure(psycopg.OperationalError()) is (
        DatabaseProbeFailure.UNREACHABLE
    )
    assert probe_failure(database_errors.UndefinedFunction()) is (
        DatabaseProbeFailure.ERROR
    )


class EmptyHeartbeats:
    def save(self, heartbeat: WorkerHeartbeatDocument) -> None:
        del heartbeat

    def find_freshest(self) -> WorkerHeartbeatDocument | None:
        return None

    def delete_beaten_before(self, beaten_before: Microseconds) -> DocumentCount:
        del beaten_before
        return DocumentCount(0)


def test_worker_pulses_are_found_and_purged_by_their_indexed_beat(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    repo = WorkerHeartbeatRepository(
        postgres_collections(WorkerHeartbeatDocument, "worker_heartbeats")
    )
    now: int = 1_790_000_000 * SECOND
    with storage_scope.platform_wide():
        old = heartbeat_at(now - 2 * 24 * 3600 * SECOND)
        fresh = heartbeat_at(now - 5 * SECOND)
        repo.save(old)
        repo.save(fresh)
        freshest = repo.find_freshest()
        deleted = repo.delete_beaten_before(Microseconds(now - 24 * 3600 * SECOND))
        remaining = repo.find_freshest()

    assert freshest is not None and freshest.id == fresh.id
    assert int(deleted) == 1
    assert remaining is not None and remaining.id == fresh.id
