"""
Hybrid ranking: the lexical scores of titles, aliases, tags and text joined
with the meaning of the query (cosine similarity of embeddings).

Both sides are brought to 0..1 first: a lexical score relative to the best
lexical match of the query, a similarity relative to the floor below which
an item is unrelated. An item found by both ranks highest; an item found
by meaning alone (a Georgian question, an English title without a
Georgian alias) needs a clearly closer meaning to count at all. Scores are
technical floats used only for ordering. The thresholds fit OpenAI's
text-embedding-3 models; live ranking quality needs an embeddings key.
"""

from collections.abc import Sequence

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.utilities.knowledge.ranking.ranked_item import RankedItem, ranking_key

LEXICAL_SHARE: float = 0.55
SEMANTIC_SHARE: float = 0.45
# Below this similarity a query and an item are unrelated.
MIN_SIMILARITY: float = 0.30
# An item no word of the query matches must be this close in meaning.
MIN_MEANING_ONLY_SIMILARITY: float = 0.40


def rank_hybrid(
    lexical: Sequence[RankedItem],
    neighbours: Sequence[KnowledgeNeighbour],
    items: Sequence[KnowledgeItemDocument],
) -> list[RankedItem]:
    """
    The items of either side, best first (see the module docstring); a
    neighbour that is not among `items` (switched off or gone since its
    vector was stored) is left out.
    """

    items_by_id: dict[str, KnowledgeItemDocument] = {
        str(item.id): item for item in items
    }
    best_lexical: float = max((ranked.score for ranked in lexical), default=0.0)
    scores: dict[str, float] = {}
    for ranked in lexical:
        if best_lexical > 0.0:
            scores[str(ranked.item.id)] = LEXICAL_SHARE * ranked.score / best_lexical

    for neighbour in neighbours:
        item_id: str = str(neighbour.item_id)
        similarity: float = float(neighbour.similarity)
        if item_id not in items_by_id or similarity < MIN_SIMILARITY:
            continue

        if item_id not in scores and similarity < MIN_MEANING_ONLY_SIMILARITY:
            continue

        meaning: float = (similarity - MIN_SIMILARITY) / (1.0 - MIN_SIMILARITY)
        scores[item_id] = scores.get(item_id, 0.0) + SEMANTIC_SHARE * meaning

    return sorted(
        (
            RankedItem(item=items_by_id[item_id], score=score)
            for item_id, score in scores.items()
            if item_id in items_by_id
        ),
        key=ranking_key,
    )
