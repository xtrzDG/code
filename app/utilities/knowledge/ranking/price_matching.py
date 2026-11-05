"""Match an asked dish, service or product name to item titles, for prices."""

from collections.abc import Sequence

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.knowledge.ranking.character_ngrams import character_ngram_dice
from app.utilities.knowledge.ranking.indexed_item import item_titles
from app.utilities.knowledge.ranking.ranked_item import RankedItem, ranking_key
from app.utilities.knowledge.ranking.token_similarity import (
    EXACT_SIMILARITY,
    best_similarity,
    weighted_coverage,
)
from app.utilities.knowledge.search_text import (
    SearchToken,
    fold_words,
    tokenize,
    unique_tokens,
)

PRICE_MATCH_THRESHOLD: float = 0.5
PRICE_QUERY_COVERAGE_SHARE: float = 0.7
PRICE_NGRAM_SHARE: float = 0.9
# Words of the asked name that match no item at all ("price", "how much")
# carry no information about which item is meant.
PRICE_UNMATCHED_TOKEN_WEIGHT: float = 0.25


def rank_price_matches(
    item_name: str,
    items: Sequence[KnowledgeItemDocument],
) -> list[RankedItem]:
    """
    Fuzzy-match a dish, service or product name to item titles, best first.

    An item is matched by its title and by each of its aliases (its title
    in the business's other languages), by the best of them. The score
    mixes how much of the asked name is found in the name, how much of the
    name is covered, and character n-gram overlap for typos. Only matches
    scoring at least PRICE_MATCH_THRESHOLD are returned, so an empty result
    honestly means "not in the price list".
    """

    query_tokens: list[SearchToken] = unique_tokens(tokenize(item_name))
    folded_name: str = fold_words(item_name)
    if query_tokens == []:
        return []

    similarity_cache: dict[tuple[str, str], float] = {}
    names_of_items: list[list[str]] = [item_titles(item) for item in items]
    query_tokens = reweight_unmatched_tokens(
        query_tokens,
        [unique_tokens(tokenize(name)) for names in names_of_items for name in names],
        similarity_cache,
    )
    ranked_items: list[RankedItem] = []
    for item, names in zip(items, names_of_items, strict=True):
        score: float = max(
            name_score(query_tokens, folded_name, name, similarity_cache)
            for name in names
        )
        if score >= PRICE_MATCH_THRESHOLD:
            ranked_items.append(RankedItem(item=item, score=score))

    return sorted(ranked_items, key=ranking_key)


def name_score(
    query_tokens: list[SearchToken],
    folded_name: str,
    name: str,
    similarity_cache: dict[tuple[str, str], float],
) -> float:
    """How well the asked name matches one name of an item (0 to 1)."""

    name_tokens: list[SearchToken] = unique_tokens(tokenize(name))
    if name_tokens == []:
        return 0.0

    folded_title: str = fold_words(name)
    if folded_title == folded_name:
        return EXACT_SIMILARITY

    query_coverage: float = weighted_coverage(
        query_tokens,
        name_tokens,
        similarity_cache,
    )
    title_coverage: float = weighted_coverage(
        name_tokens,
        query_tokens,
        similarity_cache,
    )
    token_score: float = (
        PRICE_QUERY_COVERAGE_SHARE * query_coverage
        + (1.0 - PRICE_QUERY_COVERAGE_SHARE) * title_coverage
    )
    ngram_score: float = PRICE_NGRAM_SHARE * character_ngram_dice(
        folded_name,
        folded_title,
    )
    return max(token_score, ngram_score)


def reweight_unmatched_tokens(
    query_tokens: list[SearchToken],
    titles_tokens: list[list[SearchToken]],
    similarity_cache: dict[tuple[str, str], float],
) -> list[SearchToken]:
    """Lower the weight of asked words that match no title at all."""

    reweighted: list[SearchToken] = []
    for query_token in query_tokens:
        is_matched: bool = any(
            best_similarity(query_token, title_tokens, similarity_cache) > 0.0
            for title_tokens in titles_tokens
        )
        if is_matched:
            reweighted.append(query_token)
            continue

        reweighted.append(
            SearchToken(
                text=query_token.text,
                weight=query_token.weight * PRICE_UNMATCHED_TOKEN_WEIGHT,
                allows_partial=query_token.allows_partial,
            )
        )

    return reweighted
