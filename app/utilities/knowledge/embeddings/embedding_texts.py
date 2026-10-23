"""
What a knowledge item's embedding is computed from, and the fingerprint
that says whether a stored vector is still current.
"""

import hashlib
from collections.abc import Sequence

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeEmbeddingFingerprint,
)
from app.schemas.typings.knowledge.strings import EmbeddingInputText

# The meaning of an item is in its title, aliases and the start of its text.
MAX_BODY_CHARACTERS: int = 1_500


def embedding_text(item: KnowledgeItemDocument) -> EmbeddingInputText:
    """
    The item's title, its aliases (the title in other languages), its tags
    and the start of its text, one per line.
    """

    lines: list[str] = [str(item.title)]
    if item.aliases:
        lines.append(" | ".join(str(alias.text) for alias in item.aliases))

    if item.tags:
        lines.append(", ".join(str(tag).replace("_", " ") for tag in item.tags))

    if item.body is not None and item.body.strip() != "":
        lines.append(str(item.body)[:MAX_BODY_CHARACTERS])

    return EmbeddingInputText("\n".join(lines))


def embedding_fingerprint(
    model_id: EmbeddingModelId, text: EmbeddingInputText
) -> KnowledgeEmbeddingFingerprint:
    """SHA-256 of the model and the text (a technical digest, not a secret)."""

    digest: str = hashlib.sha256(f"{model_id}\n{text}".encode()).hexdigest()
    return KnowledgeEmbeddingFingerprint(digest)


def current_neighbours(
    neighbours: Sequence[KnowledgeNeighbour],
    items: Sequence[KnowledgeItemDocument],
    model_id: EmbeddingModelId,
) -> list[KnowledgeNeighbour]:
    """
    The neighbours whose stored vector still matches the item's current
    text: an item edited since its last indexing is left to its words, not
    found by the meaning it no longer has.
    """

    items_by_id: dict[str, KnowledgeItemDocument] = {
        str(item.id): item for item in items
    }
    current: list[KnowledgeNeighbour] = []
    for neighbour in neighbours:
        item: KnowledgeItemDocument | None = items_by_id.get(str(neighbour.item_id))
        if item is not None and neighbour.fingerprint == embedding_fingerprint(
            model_id, embedding_text(item)
        ):
            current.append(neighbour)

    return current
