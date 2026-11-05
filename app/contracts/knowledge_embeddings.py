"""
The meaning side of the hybrid knowledge search: an embedding model (an EU
endpoint) and the vectors of a business's knowledge items (pgvector).

Vectors and their components are technical values of the model, used only
to rank items, and stay raw floats (AGENTS.md: technical values); the
similarity a search reports is a typed `EmbeddingSimilarity`.
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import EmbeddingNeighbourLimit
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import EmbeddingInputText

type EmbeddingVector = tuple[float, ...]
type StoredEmbedding = tuple[
    KnowledgeItemId, KnowledgeEmbeddingFingerprint, EmbeddingVector
]


class TextEmbedderContract(AdapterContract, Protocol):
    def is_enabled(self) -> bool:
        """False without an embeddings key: the search stays lexical."""
        raise NotImplementedError

    def model_id(self) -> EmbeddingModelId:
        """The model whose vectors this embedder returns."""
        raise NotImplementedError

    def embed(self, texts: Sequence[EmbeddingInputText]) -> list[EmbeddingVector]:
        """
        One vector per text, in order, from one call (at most
        `MAX_TEXTS_PER_CALL` texts).

        Raises:
            ExternalServiceError: the model is unavailable, refused or
                answered in an unexpected shape (or the embedder is off).
        """
        raise NotImplementedError


class KnowledgeEmbeddingStoreContract(AdapterContract, Protocol):
    """
    The vectors of the knowledge items, one per item, read and written only
    together with their business (row-level security on Postgres too).
    """

    def is_available(self) -> bool:
        """False on a database without pgvector: nothing is stored or found."""
        raise NotImplementedError

    def read_fingerprints(
        self, business_id: BusinessId
    ) -> dict[KnowledgeItemId, KnowledgeEmbeddingFingerprint]:
        """
        What each stored vector of the business was computed from (the
        fingerprint covers the model, so a vector of another model is stale).
        """
        raise NotImplementedError

    def save(
        self,
        business_id: BusinessId,
        model_id: EmbeddingModelId,
        embeddings: Sequence[StoredEmbedding],
    ) -> None:
        """Store (or replace) the vectors of these items, in one transaction."""
        raise NotImplementedError

    def delete(
        self, business_id: BusinessId, item_ids: Sequence[KnowledgeItemId]
    ) -> None:
        """Forget the vectors of these items (gone, switched off)."""
        raise NotImplementedError

    def nearest(
        self,
        business_id: BusinessId,
        model_id: EmbeddingModelId,
        query: EmbeddingVector,
        limit: EmbeddingNeighbourLimit,
    ) -> list[KnowledgeNeighbour]:
        """
        The business's items of `model_id` most similar to the query (cosine
        similarity), most similar first, at most `limit`.
        """
        raise NotImplementedError
