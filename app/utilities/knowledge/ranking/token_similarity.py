"""Similarity of two folded search tokens, in [0, 1].

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

from app.utilities.knowledge.search_text import SearchToken, has_prefixed_particles

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
