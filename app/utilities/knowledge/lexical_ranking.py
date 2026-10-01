"""Lexical ranking of knowledge items without external models.

Scores are technical floats used only for ordering. The concept's next step
is pgvector embeddings; they will sit behind the same use-case contracts.

Token similarity:
- exact token: 1.0
- one token is a prefix of the other (at least 3 characters): 0.8, which
  covers inflection ("салат" / "салаты", "ხაჭაპური" / "ხაჭაპურის")
- long common prefix (at least 4 characters and 70% of the shorter token): 0.7
- in Hebrew and Arabic, the shorter token (at least 4 characters) ends the
  longer one after at most 3 prefix particles ("הפיצה", "الفلافل"): 0.7
- one typo (two for long words) by Damerau-Levenshtein distance, with the
  same first letter so that "price" does not match "rice": 0.6
Character n-grams of space-less scripts match only exactly.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.knowledge.search_text import (
    SearchToken,
    contains_phrase,
    fold_text,
    fold_words,
    has_prefixed_particles,
    is_space_less_character,
    tokenize,
    unique_tokens,
)

EXACT_SIMILARITY: float = 1.0
PREFIX_SIMILARITY: float = 0.8
STEM_SIMILARITY: float = 0.7
TYPO_SIMILARITY: float = 0.6
MIN_PREFIX_LENGTH: int = 3
MIN_STEM_LENGTH: int = 4
STEM_SHARE: float = 0.7
MAX_PREFIX_PARTICLE_LENGTH: int = 3
MIN_TYPO_LENGTH: int = 4
LONG_WORD_LENGTH: int = 8
DOCUMENT_FREQUENCY_SIMILARITY: float = PREFIX_SIMILARITY

TITLE_WEIGHT: float = 3.0
TAG_WEIGHT: float = 2.0
ATTRIBUTE_WEIGHT: float = 1.5
BODY_WEIGHT: float = 1.0
PHRASE_BONUS: float = 1.5
LANGUAGE_BONUS: float = 1.1

PRICE_MATCH_THRESHOLD: float = 0.5
PRICE_QUERY_COVERAGE_SHARE: float = 0.7
PRICE_NGRAM_SHARE: float = 0.9
# Words of the asked name that match no item at all ("price", "how much")
# carry no information about which item is meant.
PRICE_UNMATCHED_TOKEN_WEIGHT: float = 0.25


@dataclass(frozen=True)
class RankedItem:
    """A knowledge item with its technical relevance score."""

    item: KnowledgeItemDocument
    score: float


@dataclass(frozen=True)
class IndexedItem:
    """Tokens of one item, by field."""

    item: KnowledgeItemDocument
    title_tokens: list[SearchToken]
    tag_tokens: list[SearchToken]
    attribute_tokens: list[SearchToken]
    body_tokens: list[SearchToken]

    def fields(self) -> list[tuple[float, list[SearchToken]]]:
        return [
            (TITLE_WEIGHT, self.title_tokens),
            (TAG_WEIGHT, self.tag_tokens),
            (ATTRIBUTE_WEIGHT, self.attribute_tokens),
            (BODY_WEIGHT, self.body_tokens),
        ]


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


def rank_price_matches(
    item_name: str,
    items: Sequence[KnowledgeItemDocument],
) -> list[RankedItem]:
    """
    Fuzzy-match a dish, service or product name to item titles, best first.

    The score mixes how much of the asked name is found in the title, how
    much of the title is covered, and character n-gram overlap for typos.
    Only matches scoring at least PRICE_MATCH_THRESHOLD are returned, so an
    empty result honestly means "not in the price list".
    """

    query_tokens: list[SearchToken] = unique_tokens(tokenize(item_name))
    folded_name: str = fold_words(item_name)
    if query_tokens == []:
        return []

    similarity_cache: dict[tuple[str, str], float] = {}
    titles_tokens: list[list[SearchToken]] = [
        unique_tokens(tokenize(item.title)) for item in items
    ]
    query_tokens = reweight_unmatched_tokens(
        query_tokens,
        titles_tokens,
        similarity_cache,
    )
    ranked_items: list[RankedItem] = []
    for item, title_tokens in zip(items, titles_tokens, strict=True):
        if title_tokens == []:
            continue

        folded_title: str = fold_words(item.title)
        if folded_title == folded_name:
            ranked_items.append(RankedItem(item=item, score=EXACT_SIMILARITY))
            continue

        query_coverage: float = weighted_coverage(
            query_tokens,
            title_tokens,
            similarity_cache,
        )
        title_coverage: float = weighted_coverage(
            title_tokens,
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
        score: float = max(token_score, ngram_score)
        if score >= PRICE_MATCH_THRESHOLD:
            ranked_items.append(RankedItem(item=item, score=score))

    return sorted(ranked_items, key=ranking_key)


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


def ranking_key(ranked_item: RankedItem) -> tuple[float, str, str]:
    """Best score first; ties ordered by folded title, then id (stable)."""

    return (
        -ranked_item.score,
        fold_text(ranked_item.item.title),
        str(ranked_item.item.id),
    )


def index_item(item: KnowledgeItemDocument) -> IndexedItem:
    attribute_text: str = " ".join(
        f"{attribute.key} {attribute.value}" for attribute in item.attributes
    )
    return IndexedItem(
        item=item,
        title_tokens=unique_tokens(tokenize(item.title)),
        tag_tokens=unique_tokens(
            tokenize(" ".join(tag.replace("_", " ") for tag in item.tags))
        ),
        attribute_tokens=unique_tokens(tokenize(attribute_text.replace("_", " "))),
        body_tokens=unique_tokens(tokenize(item.body or "")),
    )


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


def best_similarity(
    query_token: SearchToken,
    field_tokens: list[SearchToken],
    similarity_cache: dict[tuple[str, str], float],
) -> float:
    best: float = 0.0
    for field_token in field_tokens:
        best = max(best, cached_similarity(query_token, field_token, similarity_cache))
        if best >= EXACT_SIMILARITY:
            break

    return best


def cached_similarity(
    first: SearchToken,
    second: SearchToken,
    similarity_cache: dict[tuple[str, str], float],
) -> float:
    cache_key: tuple[str, str] = (first.text, second.text)
    cached: float | None = similarity_cache.get(cache_key)
    if cached is not None:
        return cached

    similarity: float = token_similarity(first, second)
    similarity_cache[cache_key] = similarity
    return similarity


def token_similarity(first: SearchToken, second: SearchToken) -> float:
    """Similarity of two folded tokens in [0, 1] (see the module docstring)."""

    if first.text == second.text:
        return EXACT_SIMILARITY

    if not (first.allows_partial and second.allows_partial):
        return 0.0

    shorter, longer = sorted((first.text, second.text), key=len)
    if len(shorter) >= MIN_PREFIX_LENGTH and longer.startswith(shorter):
        return PREFIX_SIMILARITY

    if len(shorter) >= MIN_STEM_LENGTH:
        shared_prefix_length: int = common_prefix_length(shorter, longer)
        if (
            shared_prefix_length >= MIN_STEM_LENGTH
            and shared_prefix_length >= STEM_SHARE * len(shorter)
        ):
            return STEM_SIMILARITY

        if (
            has_prefixed_particles(longer)
            and longer.endswith(shorter)
            and len(longer) - len(shorter) <= MAX_PREFIX_PARTICLE_LENGTH
        ):
            return STEM_SIMILARITY

    if len(shorter) >= MIN_TYPO_LENGTH and shorter[0] == longer[0]:
        allowed_edits: int = 2 if len(shorter) >= LONG_WORD_LENGTH else 1
        if len(longer) - len(shorter) <= allowed_edits and (
            bounded_edit_distance(shorter, longer, allowed_edits) <= allowed_edits
        ):
            return TYPO_SIMILARITY

    return 0.0


def common_prefix_length(first: str, second: str) -> int:
    length: int = 0
    for first_character, second_character in zip(first, second, strict=False):
        if first_character != second_character:
            break

        length += 1

    return length


def bounded_edit_distance(first: str, second: str, limit: int) -> int:
    """
    Optimal string alignment distance (Damerau-Levenshtein with adjacent swaps).

    Returns `limit + 1` as soon as the distance is known to exceed `limit`.
    """

    previous_previous_row: list[int] = []
    previous_row: list[int] = list(range(len(second) + 1))
    for first_index in range(1, len(first) + 1):
        current_row: list[int] = [first_index] + [0] * len(second)
        for second_index in range(1, len(second) + 1):
            substitution_cost: int = (
                0 if first[first_index - 1] == second[second_index - 1] else 1
            )
            current_row[second_index] = min(
                previous_row[second_index] + 1,
                current_row[second_index - 1] + 1,
                previous_row[second_index - 1] + substitution_cost,
            )
            if (
                first_index > 1
                and second_index > 1
                and first[first_index - 1] == second[second_index - 2]
                and first[first_index - 2] == second[second_index - 1]
            ):
                current_row[second_index] = min(
                    current_row[second_index],
                    previous_previous_row[second_index - 2] + 1,
                )

        if min(current_row) > limit:
            return limit + 1

        previous_previous_row = previous_row
        previous_row = current_row

    return previous_row[-1]


def weighted_coverage(
    tokens: list[SearchToken],
    other_tokens: list[SearchToken],
    similarity_cache: dict[tuple[str, str], float],
) -> float:
    """Weighted share of `tokens` found among `other_tokens` (0..1)."""

    total_weight: float = sum(token.weight for token in tokens)
    if total_weight == 0.0:
        return 0.0

    covered_weight: float = sum(
        token.weight * best_similarity(token, other_tokens, similarity_cache)
        for token in tokens
    )
    return covered_weight / total_weight


def character_ngram_dice(first: str, second: str) -> float:
    """
    Dice coefficient of character n-grams of two folded strings.

    Trigrams for spaced scripts, bigrams when a string contains a space-less
    script (Chinese, Japanese, Thai...), where single words are short.
    """

    has_space_less_text: bool = any(
        is_space_less_character(character) for character in first + second
    )
    size: int = 2 if has_space_less_text else 3
    first_ngrams: list[str] = character_ngrams(first, size)
    second_ngrams: list[str] = character_ngrams(second, size)
    if first_ngrams == [] or second_ngrams == []:
        return 0.0

    remaining: list[str] = list(second_ngrams)
    shared_count: int = 0
    for ngram in first_ngrams:
        if ngram in remaining:
            remaining.remove(ngram)
            shared_count += 1

    return 2.0 * shared_count / (len(first_ngrams) + len(second_ngrams))


def character_ngrams(text: str, size: int) -> list[str]:
    padded: str = f" {text} "
    if len(padded) < size:
        return []

    return [padded[index : index + size] for index in range(len(padded) - size + 1)]


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
