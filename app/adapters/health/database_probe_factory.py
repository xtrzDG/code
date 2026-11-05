"""Choose the readiness probe for the container wiring."""

from app.adapters.health.in_memory_database_probe_adapter import (
    InMemoryDatabaseProbeAdapter,
)
from app.adapters.health.postgres_database_probe_adapter import (
    PostgresDatabaseProbeAdapter,
)
from app.adapters.health.two_pool_database_probe_adapter import (
    TwoPoolDatabaseProbeAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.health import DatabaseProbeAdapterContract


def build_database_probe_adapter(
    connection_pools: PostgresConnectionPools | None,
) -> DatabaseProbeAdapterContract:
    """
    The Postgres probe over the process's pools (both the tenant and the
    platform pool when they are two), or SKIPPED without a database.
    """

    if connection_pools is None:
        return InMemoryDatabaseProbeAdapter()

    tenant_probe = PostgresDatabaseProbeAdapter(connection_pools.tenant)
    if connection_pools.is_single:
        return tenant_probe

    return TwoPoolDatabaseProbeAdapter(
        tenant_probe, PostgresDatabaseProbeAdapter(connection_pools.platform)
    )
