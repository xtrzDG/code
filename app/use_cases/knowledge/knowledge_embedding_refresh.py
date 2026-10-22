"""
Keeping a business's knowledge vectors current: what changed is embedded
again, what is gone is forgotten, what is unchanged costs nothing.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.knowledge_embeddings import (
    EmbeddingVector,
    KnowledgeEmbeddingStoreContract,
    StoredEmbedding,
    TextEmbedderContract,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import EmbeddingInputText
from app.utilities.knowledge.embeddings.embedding_texts import (
    embedding_fingerprint,
    embedding_text,
)

# Texts of one embeddings call (the embedder takes at most 64).
EMBEDDING_BATCH_SIZE: int = 64


@dataclass(frozen=True)
class EmbeddingRefreshOutcome:
    """Vectors computed again and vectors forgotten by one refresh."""

    embedded_count: int
    forgotten_count: int


def refresh_embeddings(
    text_embedder: TextEmbedderContract,
    embedding_store: KnowledgeEmbeddingStoreContract,
    business_id: BusinessId,
    items: Sequence[KnowledgeItemDocument],
) -> EmbeddingRefreshOutcome:
    """
    The vectors of `items` (the business's active knowledge) made current:
    an item whose text (title, aliases, tags, start of its text) or model
    changed is embedded again, in calls of `EMBEDDING_BATCH_SIZE`; vectors
    of items no longer among them are deleted. Nothing happens without an
    embeddings key or without pgvector.

    Raises:
        ExternalServiceError: the embeddings endpoint failed (what was saved
            before the failure stays; the next run continues).
    """

    if not text_embedder.is_enabled() or not embedding_store.is_available():
        return EmbeddingRefreshOutcome(embedded_count=0, forgotten_count=0)

    model_id: EmbeddingModelId = text_embedder.model_id()
    stored: dict[KnowledgeItemId, KnowledgeEmbeddingFingerprint] = (
        embedding_store.read_fingerprints(business_id)
    )
    wanted: dict[
        KnowledgeItemId, tuple[KnowledgeEmbeddingFingerprint, EmbeddingInputText]
    ] = {}
    for item in items:
        text: EmbeddingInputText = embedding_text(item)
        wanted[item.id] = (embedding_fingerprint(model_id, text), text)

    stale: list[
        tuple[KnowledgeItemId, KnowledgeEmbeddingFingerprint, EmbeddingInputText]
    ] = [
        (item_id, fingerprint, text)
        for item_id, (fingerprint, text) in wanted.items()
        if stored.get(item_id) != fingerprint
    ]
    for start in range(0, len(stale), EMBEDDING_BATCH_SIZE):
        batch = stale[start : start + EMBEDDING_BATCH_SIZE]
        vectors: list[EmbeddingVector] = text_embedder.embed(
            [text for _, _, text in batch]
        )
        entries: list[StoredEmbedding] = [
            (item_id, fingerprint, vector)
            for (item_id, fingerprint, _), vector in zip(batch, vectors, strict=True)
        ]
        embedding_store.save(business_id, model_id, entries)

    gone: list[KnowledgeItemId] = [
        item_id for item_id in stored if item_id not in wanted
    ]
    embedding_store.delete(business_id, gone)
    return EmbeddingRefreshOutcome(embedded_count=len(stale), forgotten_count=len(gone))
