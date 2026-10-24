from collections.abc import Sequence

from app.contracts.knowledge_embeddings import EmbeddingVector, TextEmbedderContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.dto.resilience import CircuitBreakerPolicy
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.schemas.typings.knowledge.strings import EmbeddingInputText
from app.schemas.typings.resilience.constrained_integers import (
    CircuitFailureThreshold,
    CircuitOpenSeconds,
    CircuitWindowSeconds,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName

# Searches embed their query while a customer waits: after three failures
# within a minute the endpoint is left alone for 30 s (one trial then), so
# an outage costs three short waits, not one per search.
QUERY_EMBEDDINGS_CIRCUIT_POLICY: CircuitBreakerPolicy = CircuitBreakerPolicy(
    failure_threshold=CircuitFailureThreshold(3),
    window_seconds=CircuitWindowSeconds(60),
    open_seconds=CircuitOpenSeconds(30),
)


class CircuitTextEmbedderAdapter(TextEmbedderContract):
    """
    The query embedder behind a circuit breaker: while the circuit is open
    `embed` fails at once without a call, and the search stays lexical
    instead of waiting out a timeout every time.
    """

    def __init__(
        self,
        embedder: TextEmbedderContract,
        circuit_breaker: CircuitBreakerContract,
    ) -> None:
        self._embedder: TextEmbedderContract = embedder
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = CircuitName(f"embeddings:{embedder.model_id()}")

    def is_enabled(self) -> bool:
        return self._embedder.is_enabled()

    def model_id(self) -> EmbeddingModelId:
        return self._embedder.model_id()

    def embed(self, texts: Sequence[EmbeddingInputText]) -> list[EmbeddingVector]:
        if not self._circuit_breaker.allows_call(self._circuit):
            raise ExternalServiceError(
                "Knowledge embeddings are paused after recent failures."
            )

        try:
            vectors: list[EmbeddingVector] = self._embedder.embed(texts)
        except ExternalServiceError:
            self._circuit_breaker.record_failure(self._circuit)
            raise

        self._circuit_breaker.record_success(self._circuit)
        return vectors
