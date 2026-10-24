import time
from collections.abc import Callable

import psycopg
from psycopg import errors as database_errors
from psycopg.rows import TupleRow

from app.adapters.storage.postgres.postgres_session_settings import (
    DOCUMENT_SCHEMA_NAME,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.health import DatabaseProbeAdapterContract
from app.schemas.constants.observability import DatabaseProbeFailure, HealthCheckStatus
from app.schemas.dto.health import DatabaseProbe
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    DatabaseConnectionCount,
    DatabasePoolSize,
    ElapsedMilliseconds,
)
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName

# Readiness must answer fast: a database slower than this is not ready.
PROBE_TIMEOUT_SECONDS: float = 2.0
MIGRATIONS_TABLE: str = f"{DOCUMENT_SCHEMA_NAME}.schema_migrations"


class PostgresDatabaseProbeAdapter(DatabaseProbeAdapterContract):
    """
    The readiness probe over the process's own pool: it waits at most
    PROBE_TIMEOUT_SECONDS for a free connection (all of them busy for that
    long is POOL_EXHAUSTED), and the server cancels `select 1` and the read
    of `workshop.schema_migrations` after the same time (statement timeout
    of this transaction only).
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
        monotonic_seconds: Callable[[], float] = time.monotonic,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._timeout_seconds: float = timeout_seconds
        self._monotonic_seconds: Callable[[], float] = monotonic_seconds

    def probe(self) -> DatabaseProbe:
        in_use: DatabaseConnectionCount = self._connections_in_use()
        pool_size = DatabasePoolSize(self._connection_pool.max_size)
        started_at: float = self._monotonic_seconds()
        try:
            applied: list[SchemaMigrationName] = self._read_applied_migrations()
        except ExternalServiceError:
            return DatabaseProbe(
                status=HealthCheckStatus.FAILED,
                failure=self._describe_acquire_failure(),
                connections_in_use=in_use,
                pool_size=pool_size,
            )
        except database_errors.QueryCanceled:
            return self._failed(DatabaseProbeFailure.TIMEOUT, in_use, pool_size)
        except psycopg.OperationalError:
            return self._failed(DatabaseProbeFailure.UNREACHABLE, in_use, pool_size)
        except psycopg.Error:
            return self._failed(DatabaseProbeFailure.ERROR, in_use, pool_size)

        elapsed_seconds: float = self._monotonic_seconds() - started_at
        return DatabaseProbe(
            status=HealthCheckStatus.OK,
            latency=ElapsedMilliseconds(max(0, round(elapsed_seconds * 1000))),
            applied_migrations=applied,
            connections_in_use=in_use,
            pool_size=pool_size,
        )

    def _read_applied_migrations(self) -> list[SchemaMigrationName]:
        timeout_milliseconds: str = str(round(self._timeout_seconds * 1000))
        with (
            self._connection_pool.connection(
                acquire_timeout_seconds=self._timeout_seconds
            ) as connection,
            connection.transaction(),
        ):
            connection.execute(
                "select set_config('statement_timeout', %s, true)",
                (timeout_milliseconds,),
            )
            connection.execute("select 1")
            return read_migration_names(connection)

    def _connections_in_use(self) -> DatabaseConnectionCount:
        return DatabaseConnectionCount(
            max(
                0,
                self._connection_pool.open_connection_count()
                - self._connection_pool.idle_connection_count(),
            )
        )

    def _describe_acquire_failure(self) -> DatabaseProbeFailure:
        """No connection: all borrowed (exhausted), else none could be opened."""

        if int(self._connections_in_use()) >= self._connection_pool.max_size:
            return DatabaseProbeFailure.POOL_EXHAUSTED

        return DatabaseProbeFailure.UNREACHABLE

    def _failed(
        self,
        failure: DatabaseProbeFailure,
        in_use: DatabaseConnectionCount,
        pool_size: DatabasePoolSize,
    ) -> DatabaseProbe:
        return DatabaseProbe(
            status=HealthCheckStatus.FAILED,
            failure=failure,
            connections_in_use=in_use,
            pool_size=pool_size,
        )


def read_migration_names(connection: PostgresConnection) -> list[SchemaMigrationName]:
    """Names in `workshop.schema_migrations`; none before the first migration."""

    exists_row: TupleRow | None = connection.execute(
        "select to_regclass(%s) is not null", (MIGRATIONS_TABLE,)
    ).fetchone()
    if exists_row is None or not exists_row[0]:
        return []

    rows: list[TupleRow] = connection.execute(
        "select name from workshop.schema_migrations order by name"
    ).fetchall()
    return [SchemaMigrationName(str(row[0])) for row in rows]
