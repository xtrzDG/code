"""What the meaning side of the hybrid knowledge search returns."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.knowledge.constrained_floats import EmbeddingSimilarity
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


class KnowledgeNeighbour(ImmutableDTO):
    """A knowledge item and how close its meaning is to the query."""

    item_id: KnowledgeItemId
    similarity: EmbeddingSimilarity
