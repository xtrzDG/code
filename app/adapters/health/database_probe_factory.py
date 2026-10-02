"""Choose the readiness probe for the container wiring."""

from app.adapters.health.in_memory_database_probe_adapter import (
    InMemoryDatabaseProbeAdapter,
)
from app.adapters.health.postgres_database_probe_adapter import (
    PostgresDatabaseProbeAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.health import DatabaseProbeAdapterContract


def build_database_probe_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
) -> DatabaseProbeAdapterContract:
    """The Postgres probe over the shared pool, or SKIPPED without a database."""

    if connection_pool is None:
        return InMemoryDatabaseProbeAdapter()

    return PostgresDatabaseProbeAdapter(connection_pool)
