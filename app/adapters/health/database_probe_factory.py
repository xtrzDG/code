"""Choose the readiness probe for the container wiring."""

from app.adapters.health.in_memory_database_probe_adapter import (
    InMemoryDatabaseProbeAdapter,
)
from app.adapters.health.postgres_database_probe_adapter import (
    PostgresDatabaseProbeAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.health import DatabaseProbeAdapterContract


def build_database_probe_adapter(
    connection_pools: PostgresConnectionPools | None,
) -> DatabaseProbeAdapterContract:
    """
    The Postgres probe over the tenant pool (the one requests for a
    business wait for), or SKIPPED without a database.
    """

    if connection_pools is None:
        return InMemoryDatabaseProbeAdapter()

    return PostgresDatabaseProbeAdapter(connection_pools.tenant)
