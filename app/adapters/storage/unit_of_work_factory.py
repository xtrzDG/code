"""Choose the storage unit of work and read session for the container wiring."""

from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.storage import (
    StorageReadSessionContract,
    StorageScopeContract,
    StorageUnitOfWorkContract,
)


def build_unit_of_work_adapter(
    connection_pools: PostgresConnectionPools | None,
    storage_scope: StorageScopeContract,
) -> StorageUnitOfWorkContract | None:
    """
    One Postgres transaction per block over the pool of the block's scope;
    None without a database (in-memory writes have no transaction to group
    them in).
    """

    if connection_pools is None:
        return None

    return PostgresUnitOfWorkAdapter(connection_pools, storage_scope)


def build_read_session_adapter(
    connection_pools: PostgresConnectionPools | None,
    storage_scope: StorageScopeContract,
) -> StorageReadSessionContract | None:
    """
    Several reads in one Postgres transaction; None without a database
    (in-memory reads have no round trips to save).
    """

    if connection_pools is None:
        return None

    return PostgresReadSessionAdapter(connection_pools, storage_scope)
