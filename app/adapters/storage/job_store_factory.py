"""
Choose the job queue stores for the container wiring: Postgres when the
process has a connection pool (DATABASE_URL), the in-process twins over the
in-memory collections otherwise.
"""

from app.adapters.storage.in_memory_periodic_job_run_store_adapter import (
    InMemoryPeriodicJobRunStoreAdapter,
)
from app.adapters.storage.in_memory_queued_job_claim_adapter import (
    InMemoryQueuedJobClaimAdapter,
)
from app.adapters.storage.postgres.postgres_periodic_job_run_store_adapter import (
    PostgresPeriodicJobRunStoreAdapter,
)
from app.adapters.storage.postgres.postgres_queued_job_claim_adapter import (
    PostgresQueuedJobClaimAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.jobs import (
    PeriodicJobRunStoreAdapterContract,
    QueuedJobClaimAdapterContract,
)
from app.schemas.domain.jobs import PeriodicJobRunDocument, QueuedJobDocument


def build_queued_job_claim_adapter(
    collection: DocumentCollectionAdapterContract[QueuedJobDocument],
    connection_pool: PostgresConnectionPoolClient | None,
) -> QueuedJobClaimAdapterContract:
    if connection_pool is None:
        return InMemoryQueuedJobClaimAdapter(collection)

    return PostgresQueuedJobClaimAdapter(connection_pool)


def build_periodic_job_run_store_adapter(
    collection: DocumentCollectionAdapterContract[PeriodicJobRunDocument],
    connection_pool: PostgresConnectionPoolClient | None,
) -> PeriodicJobRunStoreAdapterContract:
    if connection_pool is None:
        return InMemoryPeriodicJobRunStoreAdapter(collection)

    return PostgresPeriodicJobRunStoreAdapter(collection, connection_pool)
