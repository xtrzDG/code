from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.schemas.typings.platform.strings import PlatformSecret

DEFAULT_EMBEDDINGS_MODEL_ID: str = "text-embedding-3-small"


class EmbeddingSettings(ImmutableDTO):
    """
    The meaning side of the hybrid knowledge search: the key of the
    embeddings endpoint (EMBEDDINGS_API_KEY, the same EU data-residency
    project as the language model, at OPENAI_BASE_URL) and its model
    (EMBEDDINGS_MODEL_ID). Without a key the search stays lexical: titles,
    aliases, tags and text, in any language the owner wrote them in.
    """

    api_key: PlatformSecret | None = None
    model_id: EmbeddingModelId = EmbeddingModelId(DEFAULT_EMBEDDINGS_MODEL_ID)
