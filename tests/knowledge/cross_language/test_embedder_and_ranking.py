"""
The embedder's checks of the model's vectors, the vector maths, and how the
hybrid ranking joins words and meaning.
"""

import math

import pytest

from app.adapters.embeddings.disabled_text_embedder_adapter import (
    DisabledTextEmbedderAdapter,
)
from app.adapters.embeddings.openai_text_embedder_adapter import (
    MAX_TEXT_CHARACTERS,
    OpenAiTextEmbedderAdapter,
)
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.constrained_floats import EmbeddingSimilarity
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import EmbeddingInputText
from app.utilities.knowledge.embeddings.vector_math import (
    cosine_similarity,
    to_similarity,
    vector_literal,
)
from app.utilities.knowledge.ranking.hybrid_ranking import rank_hybrid
from app.utilities.knowledge.ranking.ranked_item import RankedItem
from tests.knowledge.cross_language.world import CrossLanguageWorld

ANY_FINGERPRINT = KnowledgeEmbeddingFingerprint("0" * 64)


def neighbour(item_id: KnowledgeItemId, similarity: float) -> KnowledgeNeighbour:
    return KnowledgeNeighbour(
        item_id=item_id,
        similarity=EmbeddingSimilarity(similarity),
        fingerprint=ANY_FINGERPRINT,
    )


MODEL = EmbeddingModelId("text-embedding-3-small")


class CannedClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors: list[list[float]] = vectors
        self.texts: list[str] = []

    def create_embeddings(self, *, model: str, texts: list[str]) -> list[list[float]]:
        assert model == str(MODEL)
        self.texts = texts
        return self.vectors


def embed(vectors: list[list[float]], texts: list[str]) -> list[tuple[float, ...]]:
    adapter = OpenAiTextEmbedderAdapter(CannedClient(vectors), MODEL)
    return adapter.embed([EmbeddingInputText(text) for text in texts])


def test_vectors_of_one_length_and_finite_values_are_accepted() -> None:
    client = CannedClient([[0.5, 0.5], [1.0, 0.0]])
    adapter = OpenAiTextEmbedderAdapter(client, MODEL)

    vectors = adapter.embed([EmbeddingInputText("a" * 7_000), EmbeddingInputText("b")])

    assert vectors == [(0.5, 0.5), (1.0, 0.0)]
    assert len(client.texts[0]) == MAX_TEXT_CHARACTERS
    assert adapter.embed([]) == []


@pytest.mark.parametrize(
    "vectors",
    [[[0.5, 0.5], [1.0]], [[]], [[math.nan, 1.0]], [[math.inf, 1.0]]],
)
def test_vectors_of_different_lengths_or_non_finite_values_are_refused(
    vectors: list[list[float]],
) -> None:
    with pytest.raises(ExternalServiceError):
        embed(vectors, ["a"] * len(vectors))


def test_too_many_texts_are_refused_and_a_disabled_embedder_sends_none() -> None:
    with pytest.raises(ExternalServiceError, match="At most 64"):
        embed([[1.0]] * 65, ["a"] * 65)

    disabled = DisabledTextEmbedderAdapter(MODEL)
    assert not disabled.is_enabled()
    assert disabled.model_id() == MODEL
    with pytest.raises(ExternalServiceError, match="EMBEDDINGS_API_KEY"):
        disabled.embed([EmbeddingInputText("a")])


def test_cosine_similarity_and_the_pgvector_text_form() -> None:
    assert cosine_similarity((1.0, 0.0), (1.0, 0.0)) == pytest.approx(1.0)
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)
    assert cosine_similarity((1.0, 0.0), (1.0, 0.0, 0.0)) == 0.0
    assert cosine_similarity((0.0, 0.0), (1.0, 0.0)) == 0.0
    assert float(to_similarity(1.0000001)) == 1.0
    assert float(to_similarity(math.nan)) == 0.0
    assert vector_literal((0.5, -1e-05)) == "[0.5,-1e-05]"


def test_words_and_meaning_together_rank_first_and_weak_meanings_stay_out() -> None:
    world = CrossLanguageWorld()
    by_words = world.add_item("Do you have parking?")
    by_both = world.add_item("Parking and cars")
    by_meaning = world.add_item("Where to leave the car")
    unrelated = world.add_item("When is the live music?")
    switched_off = world.add_item("Garage", is_active=False)
    items = [by_words, by_both, by_meaning, unrelated]

    ranked = rank_hybrid(
        [RankedItem(item=by_words, score=6.0), RankedItem(item=by_both, score=5.0)],
        [
            neighbour(by_both.id, 0.8),
            neighbour(by_meaning.id, 0.7),
            neighbour(unrelated.id, 0.35),
            neighbour(switched_off.id, 0.9),
        ],
        items,
    )

    assert [str(entry.item.title) for entry in ranked] == [
        "Parking and cars",
        "Do you have parking?",
        "Where to leave the car",
    ]
