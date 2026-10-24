"""Choose how the system page measures the database for the container wiring."""

from app.adapters.monitoring.postgres_database_size_adapter import (
    PostgresDatabaseSizeAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.monitoring import DatabaseSizeAdapterContract
from app.schemas.dto.platform_health import DatabaseSize


class UnmeasuredDatabaseSizeAdapter(DatabaseSizeAdapterContract):
    """Storage in memory (tests, development without a database): no sizes."""

    def measure(self) -> DatabaseSize | None:
        return None


def build_database_size_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
) -> DatabaseSizeAdapterContract:
    if connection_pool is None:
        return UnmeasuredDatabaseSizeAdapter()

    return PostgresDatabaseSizeAdapter(connection_pool)
