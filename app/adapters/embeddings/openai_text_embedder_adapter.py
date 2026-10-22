import math
from collections.abc import Sequence

from app.contracts.embedding_clients import OpenAiEmbeddingsClientContract
from app.contracts.knowledge_embeddings import EmbeddingVector, TextEmbedderContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.schemas.typings.knowledge.strings import EmbeddingInputText

# The endpoint takes up to 2,048 inputs; a smaller batch keeps one call
# short and its failure cheap to repeat.
MAX_TEXTS_PER_CALL: int = 64
# About 2,000 tokens: a long answer's text is cut, its meaning is in front.
MAX_TEXT_CHARACTERS: int = 6_000


class OpenAiTextEmbedderAdapter(TextEmbedderContract):
    """
    Embeddings of the configured model from the OpenAI Embeddings API (the
    EU endpoint): every vector is checked to be finite and of one length.
    """

    def __init__(
        self,
        client: OpenAiEmbeddingsClientContract,
        model_id: EmbeddingModelId,
    ) -> None:
        self._client: OpenAiEmbeddingsClientContract = client
        self._model_id: EmbeddingModelId = model_id

    def is_enabled(self) -> bool:
        return True

    def model_id(self) -> EmbeddingModelId:
        return self._model_id

    def embed(self, texts: Sequence[EmbeddingInputText]) -> list[EmbeddingVector]:
        if len(texts) > MAX_TEXTS_PER_CALL:
            raise ExternalServiceError(
                f"At most {MAX_TEXTS_PER_CALL} texts are embedded in one call."
            )

        if len(texts) == 0:
            return []

        raw_vectors: list[list[float]] = self._client.create_embeddings(
            model=str(self._model_id),
            texts=[str(text)[:MAX_TEXT_CHARACTERS] for text in texts],
        )
        vectors: list[EmbeddingVector] = [
            tuple(float(value) for value in raw_vector) for raw_vector in raw_vectors
        ]
        dimensions: set[int] = {len(vector) for vector in vectors}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ExternalServiceError(
                "The embedding model answered vectors of different or no length."
            )

        if not all(math.isfinite(value) for vector in vectors for value in vector):
            raise ExternalServiceError(
                "The embedding model answered a non-finite value."
            )

        return vectors
