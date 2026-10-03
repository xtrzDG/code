"""Choose the storage unit of work for the container wiring."""

from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.storage import StorageScopeContract, StorageUnitOfWorkContract


def build_unit_of_work_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    storage_scope: StorageScopeContract,
) -> StorageUnitOfWorkContract | None:
    """
    One Postgres transaction per block over the shared pool; None without a
    database (in-memory writes have no transaction to group them in).
    """

    if connection_pool is None:
        return None

    return PostgresUnitOfWorkAdapter(connection_pool, storage_scope)
