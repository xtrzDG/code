"""A knowledge item with its relevance score, and the order of results."""

from dataclasses import dataclass

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.knowledge.search_text import fold_text


@dataclass(frozen=True)
class RankedItem:
    """A knowledge item with its technical relevance score."""

    item: KnowledgeItemDocument
    score: float


def ranking_key(ranked_item: RankedItem) -> tuple[float, str, str]:
    """Best score first; ties ordered by folded title, then id (stable)."""

    return (
        -ranked_item.score,
        fold_text(ranked_item.item.title),
        str(ranked_item.item.id),
    )
