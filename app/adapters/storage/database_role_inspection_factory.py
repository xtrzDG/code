"""Choose the startup inspection of the pools' database roles."""

from app.adapters.storage.in_memory_database_role_inspection_adapter import (
    InMemoryDatabaseRoleInspectionAdapter,
)
from app.adapters.storage.postgres.postgres_database_role_inspection_adapter import (
    PostgresDatabaseRoleInspectionAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.database_roles import DatabaseRoleInspectionAdapterContract


def build_database_role_inspection_adapter(
    connection_pools: PostgresConnectionPools | None,
) -> DatabaseRoleInspectionAdapterContract:
    if connection_pools is None:
        return InMemoryDatabaseRoleInspectionAdapter()

    return PostgresDatabaseRoleInspectionAdapter(connection_pools)
