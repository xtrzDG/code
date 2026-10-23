"""Choose the embedder for the container wiring."""

from app.adapters.embeddings.circuit_text_embedder_adapter import (
    CircuitTextEmbedderAdapter,
)
from app.adapters.embeddings.disabled_text_embedder_adapter import (
    DisabledTextEmbedderAdapter,
)
from app.adapters.embeddings.openai_text_embedder_adapter import (
    OpenAiTextEmbedderAdapter,
)
from app.contracts.embedding_clients import OpenAiEmbeddingsClientContract
from app.contracts.knowledge_embeddings import TextEmbedderContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.configurations.app_settings import AppSettings


def build_text_embedder(
    settings: AppSettings, client: OpenAiEmbeddingsClientContract
) -> TextEmbedderContract:
    """The OpenAI EU embeddings with EMBEDDINGS_API_KEY; none without it."""

    if settings.embeddings.api_key is None:
        return DisabledTextEmbedderAdapter(settings.embeddings.model_id)

    return OpenAiTextEmbedderAdapter(client, settings.embeddings.model_id)


def build_query_text_embedder(
    settings: AppSettings,
    client: OpenAiEmbeddingsClientContract,
    circuit_breaker: CircuitBreakerContract,
) -> TextEmbedderContract:
    """
    The embedder of search queries: the query client's short budget behind
    a circuit breaker, so an embeddings outage costs a search no wait.
    """

    embedder: TextEmbedderContract = build_text_embedder(settings, client)
    if not embedder.is_enabled():
        return embedder

    return CircuitTextEmbedderAdapter(embedder, circuit_breaker)
