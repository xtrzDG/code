import threading
from collections.abc import Generator, Sequence
from contextlib import contextmanager

from typed_time_provider import Microseconds, WallClock

from app.adapters.embeddings.knowledge_embedding_queries import (
    DELETE_ITEMS,
    KNOWLEDGE_EMBEDDINGS_TABLE,
    READ_AVAILABILITY,
    READ_FINGERPRINTS,
    VectorQueries,
    build_vector_queries,
)
from app.adapters.storage.postgres.platform_transaction import (
    platform_transaction,
    storage_errors_translated,
)
from app.adapters.storage.postgres.scoped_transactions import scoped_transaction
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.knowledge_embeddings import (
    EmbeddingVector,
    KnowledgeEmbeddingStoreContract,
    StoredEmbedding,
)
from app.contracts.storage import StorageScopeContract
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import EmbeddingNeighbourLimit
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.knowledge.embeddings.vector_math import to_similarity, vector_literal
from app.utilities.storage.storage_scoping import require_tenant_scope

# A database without pgvector is asked again after this long, so a table an
# administrator enabled later is found without a restart.
RECHECK_MICROSECONDS: int = 10 * 60 * 1_000_000
TABLE_LABEL: str = f"table {KNOWLEDGE_EMBEDDINGS_TABLE!r}"


class PostgresKnowledgeEmbeddingStoreAdapter(KnowledgeEmbeddingStoreContract):
    """
    The vectors in `workshop.knowledge_embeddings` (pgvector, migration
    1211), every statement in the ambient business scope under row-level
    security and filtered by business explicitly as well. A search ranks
    one business's rows exactly by cosine distance (`<=>`).

    Without pgvector (or before an administrator enabled it) the store is
    unavailable: the search stays lexical and nothing is written.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._lock: threading.Lock = threading.Lock()
        self._queries: VectorQueries | None = None
        self._checked_at: int | None = None

    def is_available(self) -> bool:
        return self._vector_queries() is not None

    def read_fingerprints(
        self, business_id: BusinessId
    ) -> dict[KnowledgeItemId, KnowledgeEmbeddingFingerprint]:
        if self._vector_queries() is None:
            return {}

        with self._transaction() as connection:
            rows = connection.execute(
                READ_FINGERPRINTS, {"business_id": str(business_id)}
            ).fetchall()

        return {
            KnowledgeItemId(str(row[0])): KnowledgeEmbeddingFingerprint(str(row[1]))
            for row in rows
        }

    def save(
        self,
        business_id: BusinessId,
        model_id: EmbeddingModelId,
        embeddings: Sequence[StoredEmbedding],
    ) -> None:
        queries: VectorQueries | None = self._vector_queries()
        if queries is None or not embeddings:
            return

        written_at: int = int(self._wall_clock.now_unix())
        parameters = [
            {
                "business_id": str(business_id),
                "item_id": str(item_id),
                "model_id": str(model_id),
                "fingerprint": str(fingerprint),
                "embedding": vector_literal(vector),
                "updated_at": written_at,
            }
            for item_id, fingerprint, vector in embeddings
        ]
        with self._transaction() as connection, connection.cursor() as cursor:
            cursor.executemany(queries.upsert, parameters)

    def delete(
        self, business_id: BusinessId, item_ids: Sequence[KnowledgeItemId]
    ) -> None:
        if self._vector_queries() is None or not item_ids:
            return

        with self._transaction() as connection:
            connection.execute(
                DELETE_ITEMS,
                {
                    "business_id": str(business_id),
                    "item_ids": [str(item_id) for item_id in item_ids],
                },
            )

    def nearest(
        self,
        business_id: BusinessId,
        model_id: EmbeddingModelId,
        query: EmbeddingVector,
        limit: EmbeddingNeighbourLimit,
    ) -> list[KnowledgeNeighbour]:
        queries: VectorQueries | None = self._vector_queries()
        if queries is None or len(query) == 0:
            return []

        with self._transaction() as connection:
            rows = connection.execute(
                queries.nearest,
                {
                    "business_id": str(business_id),
                    "model_id": str(model_id),
                    "query": vector_literal(query),
                    "dimensions": len(query),
                    "limit": int(limit),
                },
            ).fetchall()

        return [
            KnowledgeNeighbour(
                item_id=KnowledgeItemId(str(row[0])),
                similarity=to_similarity(float(row[1])),
                fingerprint=KnowledgeEmbeddingFingerprint(str(row[2])),
            )
            for row in rows
        ]

    @contextmanager
    def _transaction(self) -> Generator[PostgresConnection]:
        scope = require_tenant_scope(self._storage_scope.current(), TABLE_LABEL)
        with (
            storage_errors_translated(KNOWLEDGE_EMBEDDINGS_TABLE),
            scoped_transaction(self._connection_pool, scope) as connection,
        ):
            yield connection

    def _vector_queries(self) -> VectorQueries | None:
        """The statements, once pgvector and the table are found (cached)."""

        now: int = int(self._wall_clock.now_unix())
        with self._lock:
            if self._queries is not None:
                return self._queries

            if (
                self._checked_at is not None
                and now - self._checked_at < RECHECK_MICROSECONDS
            ):
                return None

            self._checked_at = now
            with platform_transaction(
                self._connection_pool, KNOWLEDGE_EMBEDDINGS_TABLE
            ) as connection:
                row = connection.execute(READ_AVAILABILITY).fetchone()

            if row is not None and row[1] is True:
                self._queries = build_vector_queries(str(row[0]))

            return self._queries
