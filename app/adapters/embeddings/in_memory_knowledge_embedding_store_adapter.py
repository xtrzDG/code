import threading
from collections.abc import Sequence

from app.contracts.knowledge_embeddings import (
    EmbeddingVector,
    KnowledgeEmbeddingStoreContract,
    StoredEmbedding,
)
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import EmbeddingNeighbourLimit
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.knowledge.embeddings.vector_math import (
    cosine_similarity,
    to_similarity,
)

type StoredRow = tuple[EmbeddingModelId, KnowledgeEmbeddingFingerprint, EmbeddingVector]


class InMemoryKnowledgeEmbeddingStoreAdapter(KnowledgeEmbeddingStoreContract):
    """
    The vectors of this process (tests, development without a database),
    ranked exactly as the Postgres store ranks them.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._rows: dict[BusinessId, dict[KnowledgeItemId, StoredRow]] = {}

    def is_available(self) -> bool:
        return True

    def read_fingerprints(
        self, business_id: BusinessId
    ) -> dict[KnowledgeItemId, KnowledgeEmbeddingFingerprint]:
        with self._lock:
            rows: dict[KnowledgeItemId, StoredRow] = self._rows.get(business_id, {})
            return {
                item_id: fingerprint for item_id, (_, fingerprint, _) in rows.items()
            }

    def save(
        self,
        business_id: BusinessId,
        model_id: EmbeddingModelId,
        embeddings: Sequence[StoredEmbedding],
    ) -> None:
        with self._lock:
            rows: dict[KnowledgeItemId, StoredRow] = self._rows.setdefault(
                business_id, {}
            )
            for item_id, fingerprint, vector in embeddings:
                rows[item_id] = (model_id, fingerprint, tuple(vector))

    def delete(
        self, business_id: BusinessId, item_ids: Sequence[KnowledgeItemId]
    ) -> None:
        with self._lock:
            rows: dict[KnowledgeItemId, StoredRow] = self._rows.get(business_id, {})
            for item_id in item_ids:
                rows.pop(item_id, None)

    def nearest(
        self,
        business_id: BusinessId,
        model_id: EmbeddingModelId,
        query: EmbeddingVector,
        limit: EmbeddingNeighbourLimit,
    ) -> list[KnowledgeNeighbour]:
        with self._lock:
            candidates: list[StoredEmbedding] = [
                (item_id, fingerprint, vector)
                for item_id, (stored_model, fingerprint, vector) in self._rows.get(
                    business_id, {}
                ).items()
                if stored_model == model_id and len(vector) == len(query)
            ]

        neighbours: list[KnowledgeNeighbour] = [
            KnowledgeNeighbour(
                item_id=item_id,
                similarity=to_similarity(cosine_similarity(query, vector)),
                fingerprint=fingerprint,
            )
            for item_id, fingerprint, vector in candidates
        ]
        neighbours.sort(
            key=lambda neighbour: (-float(neighbour.similarity), str(neighbour.item_id))
        )
        return neighbours[: int(limit)]
