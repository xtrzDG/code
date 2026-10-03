"""Choose the advisory locks for the container wiring."""

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.locks.postgres_advisory_lock_adapter import (
    PostgresAdvisoryLockAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.storage import StorageScopeContract


def build_advisory_lock_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    storage_scope: StorageScopeContract,
) -> AdvisoryLockAdapterContract:
    """
    Postgres advisory locks over the shared pool, which every API instance
    and worker respects; without a database (tests, a development run
    whose documents live in this process) locks of this process.
    """

    if connection_pool is None:
        return InMemoryAdvisoryLockAdapter()

    return PostgresAdvisoryLockAdapter(
        connection_pool=connection_pool,
        unit_of_work=PostgresUnitOfWorkAdapter(connection_pool, storage_scope),
    )
