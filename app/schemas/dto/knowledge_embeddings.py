"""What the meaning side of the hybrid knowledge search returns."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.knowledge.constrained_floats import EmbeddingSimilarity
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


class KnowledgeNeighbour(ImmutableDTO):
    """
    A knowledge item, how close its meaning is to the query, and what its
    stored vector was computed from (a vector of an item edited since is
    stale and ignored).
    """

    item_id: KnowledgeItemId
    similarity: EmbeddingSimilarity
    fingerprint: KnowledgeEmbeddingFingerprint
