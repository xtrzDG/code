"""Choose where the knowledge vectors live, for the container wiring."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.embeddings.in_memory_knowledge_embedding_store_adapter import (
    InMemoryKnowledgeEmbeddingStoreAdapter,
)
from app.adapters.embeddings.postgres_knowledge_embedding_store_adapter import (
    PostgresKnowledgeEmbeddingStoreAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.knowledge_embeddings import KnowledgeEmbeddingStoreContract
from app.contracts.storage import StorageScopeContract


def build_knowledge_embedding_store(
    connection_pool: PostgresConnectionPoolClient | None,
    storage_scope: StorageScopeContract,
    wall_clock: WallClock[Microseconds],
) -> KnowledgeEmbeddingStoreContract:
    """
    pgvector in Postgres when there is a database (unavailable there without
    the extension); vectors of this process otherwise (tests, development).
    """

    if connection_pool is None:
        return InMemoryKnowledgeEmbeddingStoreAdapter()

    return PostgresKnowledgeEmbeddingStoreAdapter(
        connection_pool, storage_scope, wall_clock
    )
