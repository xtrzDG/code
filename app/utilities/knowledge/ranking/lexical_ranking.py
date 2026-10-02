"""Lexical ranking of knowledge items without external models.

Scores are technical floats used only for ordering. The concept's next step
is pgvector embeddings; they will sit behind the same use-case contracts.
How two tokens compare is described in `token_similarity`.
"""

import math
from collections.abc import Sequence

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.knowledge.ranking.indexed_item import IndexedItem, index_item
from app.utilities.knowledge.ranking.ranked_item import RankedItem, ranking_key
from app.utilities.knowledge.ranking.token_similarity import (
    PREFIX_SIMILARITY,
    best_similarity,
)
from app.utilities.knowledge.search_text import (
    SearchToken,
    contains_phrase,
    fold_text,
    fold_words,
    tokenize,
    unique_tokens,
)

DOCUMENT_FREQUENCY_SIMILARITY: float = PREFIX_SIMILARITY
PHRASE_BONUS: float = 1.5
LANGUAGE_BONUS: float = 1.1


def rank_knowledge_items(
    query: str,
    items: Sequence[KnowledgeItemDocument],
    preferred_languages: Sequence[str] = (),
) -> list[RankedItem]:
    """
    Rank items for a free-text query, best first; items with no match are left out.

    A query token counts once per item, in the field where it matches best;
    rare tokens weigh more (IDF over the given items); covering more query
    tokens and containing the whole query in the title rank higher. Items
    written in one of `preferred_languages` (or their base language) get a
    small bonus.
    """

    query_tokens: list[SearchToken] = unique_tokens(tokenize(query))
    if query_tokens == [] or items == []:
        return []

    indexed_items: list[IndexedItem] = [index_item(item) for item in items]
    similarity_cache: dict[tuple[str, str], float] = {}
    inverse_frequencies: dict[str, float] = compute_inverse_document_frequencies(
        query_tokens=query_tokens,
        indexed_items=indexed_items,
        similarity_cache=similarity_cache,
    )
    folded_query: str = fold_words(query)
    total_query_weight: float = sum(token.weight for token in query_tokens)
    preferred: set[str] = set()
    for language in preferred_languages:
        folded_language: str = fold_text(language)
        preferred.add(folded_language)
        preferred.add(folded_language.split("-")[0])

    ranked_items: list[RankedItem] = []
    for indexed_item in indexed_items:
        score: float = 0.0
        matched_weight: float = 0.0
        for query_token in query_tokens:
            best_field_score: float = 0.0
            for field_weight, field_tokens in indexed_item.fields():
                similarity: float = best_similarity(
                    query_token,
                    field_tokens,
                    similarity_cache,
                )
                best_field_score = max(best_field_score, field_weight * similarity)

            if best_field_score > 0.0:
                matched_weight += query_token.weight
                score += (
                    query_token.weight
                    * best_field_score
                    * inverse_frequencies[query_token.text]
                )

        if score <= 0.0:
            continue

        coverage: float = matched_weight / total_query_weight
        score *= 0.5 + 0.5 * coverage
        if contains_phrase(fold_words(indexed_item.item.title), folded_query):
            score *= PHRASE_BONUS

        if is_in_preferred_language(indexed_item.item, preferred):
            score *= LANGUAGE_BONUS

        ranked_items.append(RankedItem(item=indexed_item.item, score=score))

    return sorted(ranked_items, key=ranking_key)


def compute_inverse_document_frequencies(
    query_tokens: list[SearchToken],
    indexed_items: list[IndexedItem],
    similarity_cache: dict[tuple[str, str], float],
) -> dict[str, float]:
    """BM25-style IDF: tokens found in fewer items weigh more (always > 0)."""

    item_count: int = len(indexed_items)
    inverse_frequencies: dict[str, float] = {}
    for query_token in query_tokens:
        document_frequency: int = 0
        for indexed_item in indexed_items:
            if any(
                best_similarity(query_token, field_tokens, similarity_cache)
                >= DOCUMENT_FREQUENCY_SIMILARITY
                for _, field_tokens in indexed_item.fields()
            ):
                document_frequency += 1

        inverse_frequencies[query_token.text] = math.log(
            1.0 + (item_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )

    return inverse_frequencies


def is_in_preferred_language(
    item: KnowledgeItemDocument,
    preferred_languages: set[str],
) -> bool:
    if preferred_languages == set():
        return False

    for language in item.languages:
        folded_language: str = fold_text(language)
        if folded_language in preferred_languages:
            return True

        if folded_language.split("-")[0] in preferred_languages:
            return True

    return False
