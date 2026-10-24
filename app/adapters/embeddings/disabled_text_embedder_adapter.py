from collections.abc import Sequence

from app.contracts.knowledge_embeddings import EmbeddingVector, TextEmbedderContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.schemas.typings.knowledge.strings import EmbeddingInputText


class DisabledTextEmbedderAdapter(TextEmbedderContract):
    """No EMBEDDINGS_API_KEY: nothing is embedded, the search stays lexical."""

    def __init__(self, model_id: EmbeddingModelId) -> None:
        self._model_id: EmbeddingModelId = model_id

    def is_enabled(self) -> bool:
        return False

    def model_id(self) -> EmbeddingModelId:
        return self._model_id

    def embed(self, texts: Sequence[EmbeddingInputText]) -> list[EmbeddingVector]:
        del texts
        raise ExternalServiceError(
            "Knowledge embeddings are off: set EMBEDDINGS_API_KEY."
        )
