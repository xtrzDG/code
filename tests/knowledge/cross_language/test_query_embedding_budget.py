"""
A search embeds its query while a customer or a caller waits: a hanging
embeddings endpoint costs one short try, never the voice tool's 8 s, and
after a few failures the endpoint is not asked at all for a while.
"""

import socket
import threading
import time
from collections.abc import Iterator

import pytest
from typed_time_provider import MonotonicClock, Nanoseconds

from app.adapters.embeddings.circuit_text_embedder_adapter import (
    QUERY_EMBEDDINGS_CIRCUIT_POLICY,
    CircuitTextEmbedderAdapter,
)
from app.adapters.embeddings.openai_text_embedder_adapter import (
    OpenAiTextEmbedderAdapter,
)
from app.clients.openai.openai_embeddings_client import (
    QUERY_MAX_RETRIES,
    QUERY_TIMEOUT_SECONDS,
    OpenAiEmbeddingsClient,
)
from app.contracts.knowledge_embeddings import TextEmbedderContract
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.gateways.http.voice_routes import VOICE_TOOL_DEADLINE_SECONDS
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.knowledge.embedding_search_knowledge_use_case import (
    EmbeddingSearchKnowledgeUseCase,
)
from tests.knowledge.cross_language.world import CrossLanguageWorld

SECOND: int = 1_000_000_000


class Ticks:
    """A monotonic clock the test moves."""

    def __init__(self) -> None:
        self.now: int = 1_000 * SECOND

    def clock(self) -> MonotonicClock[Nanoseconds]:
        return MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: self.now,
        )


@pytest.fixture
def silent_endpoint() -> Iterator[str]:
    """A local server that accepts connections and never answers."""

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(16)
    held: list[socket.socket] = []
    stop = threading.Event()

    def accept() -> None:
        while not stop.is_set():
            try:
                connection, _ = server.accept()
            except OSError:
                return
            held.append(connection)

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.getsockname()[1]}/v1"
    stop.set()
    server.shutdown(socket.SHUT_RDWR)
    server.close()
    for connection in held:
        connection.close()
    thread.join(timeout=5)


def search_with(world: CrossLanguageWorld, embedder: TextEmbedderContract) -> None:
    world.hybrid_search = EmbeddingSearchKnowledgeUseCase(
        business_repo=world.business_repo,
        knowledge_item_repo=world.knowledge_item_repo,
        brand_knowledge_item_repo=world.brand_knowledge_repo,
        text_embedder=embedder,
        embedding_store=world.embedding_store,
    )


def test_a_hanging_endpoint_leaves_the_search_lexical_well_within_the_voice_deadline(
    silent_endpoint: str,
) -> None:
    world = CrossLanguageWorld()
    world.add_item("Do you have parking?", body="The city lot is next door.")
    world.run_index()
    client = OpenAiEmbeddingsClient(
        PlatformSecret("test-token-0000"),
        PublicBaseUrl(silent_endpoint),
        None,
        timeout_seconds=QUERY_TIMEOUT_SECONDS,
        max_retries=QUERY_MAX_RETRIES,
    )
    search_with(
        world,
        CircuitTextEmbedderAdapter(
            OpenAiTextEmbedderAdapter(client, EmbeddingModelId("concept-embedding-1")),
            CircuitBreakerFacilitator(Ticks().clock(), QUERY_EMBEDDINGS_CIRCUIT_POLICY),
        ),
    )

    started = time.monotonic()
    found = world.search("Do you have parking?", "en")
    waited = time.monotonic() - started

    assert found == ["Do you have parking?"]
    assert waited < VOICE_TOOL_DEADLINE_SECONDS / 2


def test_after_three_failures_searches_skip_the_endpoint_until_a_trial() -> None:
    world = CrossLanguageWorld()
    world.add_item("Do you have parking?", body="The city lot is next door.")
    world.run_index()
    ticks = Ticks()
    world.embedder.calls.clear()
    world.embedder.failure = ExternalServiceError("OpenAI embeddings timed out.")
    search_with(
        world,
        CircuitTextEmbedderAdapter(
            world.embedder,
            CircuitBreakerFacilitator(ticks.clock(), QUERY_EMBEDDINGS_CIRCUIT_POLICY),
        ),
    )

    for _ in range(5):
        assert world.search("Do you have parking?", "en") == ["Do you have parking?"]

    # Three failures opened the circuit: the fourth and fifth search never
    # reached the endpoint.
    assert len(world.embedder.calls) == 3

    world.embedder.failure = None
    ticks.now += int(QUERY_EMBEDDINGS_CIRCUIT_POLICY.open_seconds) * SECOND
    world.search("Где оставить машину?", "ru")
    world.search("Где оставить машину?", "ru")

    # One trial call closed it again; the next search embeds as usual.
    assert len(world.embedder.calls) == 5
