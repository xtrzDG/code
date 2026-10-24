"""Choose the storage of the post-deploy data tasks' batches."""

from app.adapters.storage.in_memory_data_task_batch_adapter import (
    InMemoryDataTaskBatchAdapter,
)
from app.adapters.storage.postgres.postgres_data_task_batch_adapter import (
    PostgresDataTaskBatchAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.data_tasks import DataTaskBatchAdapterContract


def build_data_task_batch_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
) -> DataTaskBatchAdapterContract:
    """Postgres batches with DATABASE_URL; without one there is nothing to do."""

    if connection_pool is None:
        return InMemoryDataTaskBatchAdapter()

    return PostgresDataTaskBatchAdapter(connection_pool)
