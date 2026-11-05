"""Choose where the knowledge vectors live, for the container wiring."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.embeddings.in_memory_knowledge_embedding_store_adapter import (
    InMemoryKnowledgeEmbeddingStoreAdapter,
)
from app.adapters.embeddings.postgres_knowledge_embedding_store_adapter import (
    PostgresKnowledgeEmbeddingStoreAdapter,
)
from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.contracts.knowledge_embeddings import KnowledgeEmbeddingStoreContract
from app.contracts.storage import StorageScopeContract


def build_knowledge_embedding_store(
    connection_pools: PostgresConnectionPools | None,
    storage_scope: StorageScopeContract,
    wall_clock: WallClock[Microseconds],
) -> KnowledgeEmbeddingStoreContract:
    """
    pgvector in Postgres when there is a database (unavailable there without
    the extension); vectors of this process otherwise (tests, development).
    """

    if connection_pools is None:
        return InMemoryKnowledgeEmbeddingStoreAdapter()

    return PostgresKnowledgeEmbeddingStoreAdapter(
        connection_pools, storage_scope, wall_clock
    )
